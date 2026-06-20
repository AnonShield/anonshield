#!/usr/bin/env bash
# One command to deploy this repo to the host from a dev machine.
# It syncs the code, then builds, starts, and warms the cache on the host.
#
#   ./scripts/deploy.sh <ssh-host>       # deploy to the given ssh host alias
#                                        # (define <ssh-host> in your ~/.ssh/config)
#
# It only deletes inside the code directories it manages; the host's local files
# (web/.env, web/certs, datasets, logs) are never touched.
set -euo pipefail
HOST="${1:?usage: ./scripts/deploy.sh <ssh-host>  (an alias from your ~/.ssh/config)}"
DEST="anonshield_deploy"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY=(--exclude='__pycache__' --exclude='*.pyc')

echo "[deploy] syncing code to $HOST:$DEST ..."
# Code dirs: mirror exactly (safe to --delete inside these).
rsync -az --delete "${PY[@]}" --exclude='node_modules' --exclude='.svelte-kit' --exclude='build' \
  "$ROOT/web/frontend/src/"   "$HOST:$DEST/web/frontend/src/"
rsync -az --delete "$ROOT/web/frontend/static/" "$HOST:$DEST/web/frontend/static/"
rsync -az --delete "${PY[@]}" "$ROOT/web/backend/" "$HOST:$DEST/web/backend/"
rsync -az --delete "${PY[@]}" "$ROOT/src/"         "$HOST:$DEST/src/"
# Single files: update in place, never delete siblings.
rsync -az \
  "$ROOT/web/Makefile" "$ROOT/web/warm_cache.sh" "$ROOT/web/RUNBOOK.md" \
  "$ROOT/web/docker-compose.prod.yml" "$ROOT/web/docker-compose.host.yml" \
  "$HOST:$DEST/web/"
rsync -az "$ROOT/web/frontend/Dockerfile" "$HOST:$DEST/web/frontend/Dockerfile"
rsync -az "$ROOT/pyproject.toml" "$ROOT/uv.lock" "$ROOT/anon.py" "$HOST:$DEST/"

echo "[deploy] building, starting, and warming on $HOST ..."
ssh "$HOST" "cd $DEST/web && make deploy"

echo "[deploy] done. https://anonshield.org"
