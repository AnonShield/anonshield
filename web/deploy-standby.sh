#!/usr/bin/env bash
# Deploy of the standby copy of the site, run by the "Deploy to standby" job (and usable by hand
# from a checkout on the standby host):
#   bash web/deploy-standby.sh <commit sha>
# The standby host runs the azul copy of docker-compose.a10.yml all the time, and a Cloudflare
# Worker sends the traffic there when the production host is down. Its own sync only copied the
# images that production was running, so a deploy made while production was down never reached the
# site; this updates it from GHCR on every push to main, whichever host is serving.
# There is no second copy to swap with here: the containers are recreated in place, so while the
# standby is serving, the site is down for as long as the new backend takes to start.
set -euo pipefail
TAG="$1"
SRC="$(cd "$(dirname "$0")" && pwd)"
cd "${ANON_STANDBY_DIR:-$HOME/apps/anonshield-espera}"
test -f .env || { echo "::error::$PWD/.env is missing (ANON_SECRET_KEY)"; exit 1; }
test -f espera.override.yml || { echo "::error::$PWD/espera.override.yml is missing"; exit 1; }
PORT="$(sed -n 's/^LOCAL_PORT=//p' espera.env 2>/dev/null | tail -n 1)"
PORT="${PORT:-18080}"
compose() { docker compose -f docker-compose.a10.yml -f espera.override.yml --profile azul "$@"; }

# Pull first, so the site only goes down once both images are here.
docker pull -q "ghcr.io/anonshield/anonshield-web-backend:$TAG"
docker pull -q "ghcr.io/anonshield/anonshield-web-frontend:$TAG"
mkdir -p anterior
cp .env docker-compose.a10.yml Caddyfile.a10 anterior/ 2>/dev/null || true
cp "$SRC/docker-compose.a10.yml" "$SRC/Caddyfile.a10" .
# IMAGE_TAG is what the standby's sync compares with production's; IMAGE_TAG_AZUL is what runs.
{ grep -vE '^IMAGE_TAG(_AZUL)?=' .env || true; echo "IMAGE_TAG=$TAG"; echo "IMAGE_TAG_AZUL=$TAG"; } > .env.new
chmod 600 .env.new
mv .env.new .env
compose up -d --pull never --remove-orphans

for _ in $(seq 1 60); do
	if curl -fsS "http://127.0.0.1:$PORT/api/health" 2>/dev/null | grep -q "\"version\":\"$TAG\""; then
		echo "standby reports $TAG"
		exit 0
	fi
	sleep 5
done
echo "::error::the standby copy does not report $TAG; going back to the previous version"
compose logs --tail 40 backend-azul || true
cp anterior/.env anterior/docker-compose.a10.yml anterior/Caddyfile.a10 .
compose up -d --pull never --remove-orphans || true
exit 1
