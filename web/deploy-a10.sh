#!/usr/bin/env bash
# Blue-green deploy of the site on a10, run by the "Deploy to production" job (and usable by hand):
#   bash ~/anonshield_deploy/web/deploy-a10.sh <commit sha>
# The new version starts in the copy that is stopped (azul or verde, see docker-compose.a10.yml)
# while the other one keeps serving. Once the new copy reports the new commit on /api/health, the
# old copy is drained (its health check answers 503 to the host Caddy, which then sends everyone to
# the new copy) and stopped; its worker first finishes the job it is running. If the new copy never
# reports the commit, it is stopped and the old one goes on serving: a failed deploy never reaches
# the visitors.
# The ANON_* variables only exist to rehearse a deploy next to production (another folder, project
# and ports); the defaults are production.
set -euo pipefail
TAG="$1"
PROJECT="${ANON_PROJECT:-web}"
cd "${ANON_DEPLOY_DIR:-$HOME/anonshield_deploy/web}"
touch cores.env
compose() { docker compose -p "$PROJECT" -f docker-compose.a10.yml --env-file .env --env-file cores.env "$@"; }
running() { [ -n "$(compose ps -q --status running "$1" 2>/dev/null)" ]; }
declare -A PROXY=([azul]="${ANON_PROXY_AZUL:-18080}" [verde]="${ANON_PROXY_VERDE:-18081}")
declare -A BACKEND=([azul]="${ANON_BACKEND_AZUL:-18000}" [verde]="${ANON_BACKEND_VERDE:-18001}")

# verde is first in the host Caddy: while it runs, azul gets no traffic and can be replaced.
if running caddy-verde; then new=azul old=verde; else new=verde old=azul; fi
echo "deploying $TAG to $new; $old stays up until then"
upper=$(echo "$new" | tr '[:lower:]' '[:upper:]')
{ grep -v "^IMAGE_TAG_$upper=" cores.env || true; echo "IMAGE_TAG_$upper=$TAG"; } > cores.env.new
mv cores.env.new cores.env

compose up -d --no-recreate redis
services="backend-$new worker-$new frontend-$new caddy-$new"
# A registry hiccup must not stop a deploy whose images are already here; missing ones fail below.
# shellcheck disable=SC2086
compose --profile "$new" pull --ignore-pull-failures $services
# shellcheck disable=SC2086
compose --profile "$new" up -d --no-deps --force-recreate $services

ok=""
for _ in $(seq 1 60); do
	if curl -fsS "http://127.0.0.1:${PROXY[$new]}/api/health" 2>/dev/null | grep -q "\"version\":\"$TAG\""; then ok=1; break; fi
	sleep 5
done
if [ -z "$ok" ]; then
	echo "::error::$new did not report $TAG; stopping it, $old goes on serving"
	compose --profile "$new" logs --tail 40 "backend-$new" || true
	# shellcheck disable=SC2086
	compose --profile "$new" stop $services || true
	exit 1
fi
echo "$new reports $TAG"
bash warm_cache.sh "http://127.0.0.1:${BACKEND[$new]}" || echo "warm-up failed (the first job will load the model)"

# The host Caddy checks every 3 s and trusts a copy after 2 good answers.
sleep 10
if running "caddy-$old"; then
	docker exec "$(compose ps -q "caddy-$old")" touch /tmp/drain
	# It gives up on a copy after 3 failed checks, 3 s apart.
	sleep 15
	compose --profile "$old" stop "caddy-$old" "frontend-$old" "backend-$old"
	compose --profile "$old" stop "worker-$old"
	echo "$old stopped"
fi
# The stack before blue-green (services backend, worker-fast, frontend, caddy), on the first run.
for c in "$PROJECT-caddy-1" "$PROJECT-frontend-1" "$PROJECT-backend-1" "$PROJECT-worker-fast-1"; do
	if docker ps -aq --filter "name=^${c}$" | grep -q .; then
		docker stop -t 120 "$c" >/dev/null && docker rm "$c" >/dev/null && echo "removed $c (stack before blue-green)"
	fi
done
echo "anonshield.org now served by $new ($TAG)"
