#!/usr/bin/env bash
# One command to deploy this repo to the host from a dev machine.
# It syncs the code, then builds, starts, and warms the cache on the host.
#
#   ./scripts/deploy-to-a9.sh            # deploys to host alias "a9"
#   ./scripts/deploy-to-a9.sh myhost     # deploys to a different ssh host
#
# It never touches the host's local secrets: web/.env and web/certs are preserved.
set -euo pipefail
HOST="${1:-a9}"
DEST="anonshield_deploy"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "[deploy] syncing code to $HOST:$DEST (preserving .env and certs)..."
rsync -az --delete \
  --exclude='.env' --exclude='certs/' --exclude='node_modules' --exclude='.svelte-kit' \
  --exclude='build/' --exclude='__pycache__' --exclude='*.pyc' --exclude='*.log' --exclude='*.bak*' \
  "$ROOT/web/" "$HOST:$DEST/web/"
rsync -az --delete --exclude='__pycache__' --exclude='*.pyc' "$ROOT/src/" "$HOST:$DEST/src/"
rsync -az "$ROOT/pyproject.toml" "$ROOT/uv.lock" "$ROOT/anon.py" "$HOST:$DEST/"

echo "[deploy] building, starting, and warming on $HOST..."
ssh "$HOST" "cd $DEST/web && make deploy"

echo "[deploy] done. https://anonshield.org"
