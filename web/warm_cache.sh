#!/usr/bin/env bash
# Warm the NER model cache: submit one tiny anonymization job so the transformer
# model downloads and loads now, instead of on the first real user request.
# Usage: bash warm_cache.sh [backend_url]   (default http://127.0.0.1:18000)
set -euo pipefail
URL="${1:-http://127.0.0.1:18000}"

echo "[warm] waiting for the backend to be healthy..."
for _ in $(seq 1 30); do
  curl -fsS "$URL/api/health" >/dev/null 2>&1 && break
  sleep 2
done

tmpdir="$(mktemp -d)"
tmp="$tmpdir/warmup.txt"   # the backend selects a processor by extension, so keep .txt
printf 'Contact John Doe at john@example.com or 192.168.1.10 (host web01.corp.local).\n' > "$tmp"
echo "[warm] submitting a warm-up job (downloads the model on first run, can take a few minutes)..."
resp="$(curl -fsS -F "file=@$tmp" -F "key=warmup" -F "strategy=filtered" "$URL/api/jobs" || true)"
rm -rf "$tmpdir"
jid="$(printf '%s' "$resp" | grep -oE '[a-f0-9-]{36}' | head -1 || true)"
if [ -z "$jid" ]; then
  echo "[warm] could not submit the warm-up job. Response: $resp"
  exit 1
fi

for _ in $(seq 1 90); do
  st="$(curl -fsS "$URL/api/jobs/$jid/status" || true)"
  case "$st" in
    *'"status":"done"'*)  echo "[warm] model loaded, cache is warm."; exit 0 ;;
    *'"status":"error"'*) echo "[warm] warm-up job errored: $st"; exit 1 ;;
  esac
  sleep 5
done
echo "[warm] still running after the timeout; the model may still be downloading. Check: make logs SVC=worker-fast"
