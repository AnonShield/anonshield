#!/usr/bin/env bash
# Poll for open pull requests and alert when the set changes. Dependabot opens
# PRs shortly after each push to main, so this catches them within a few minutes.
#
# Usage:
#   ./scripts/watch-prs.sh                       # poll AnonShield/anonshield every 5 min
#   ./scripts/watch-prs.sh OWNER/REPO 120        # custom repo and interval (seconds)
#
# Alerts via a terminal bell, a desktop notification (notify-send, if available),
# and stdout. Requires the GitHub CLI (gh) to be installed and authenticated.
set -uo pipefail

REPO="${1:-AnonShield/anonshield}"
INTERVAL="${2:-300}"
seen=""

command -v gh >/dev/null 2>&1 || { echo "watch-prs: GitHub CLI (gh) is required" >&2; exit 1; }
echo "[watch-prs] watching $REPO every ${INTERVAL}s. Press Ctrl+C to stop."

while true; do
  prs=$(gh pr list --repo "$REPO" --state open \
        --json number,title,author \
        --jq '[.[] | "#\(.number) \(.title) (@\(.author.login))"] | join("\n")' 2>/dev/null)
  if [ -n "$prs" ]; then
    nums=$(printf '%s\n' "$prs" | grep -oE '^#[0-9]+' | sort | tr '\n' ',')
    if [ "$nums" != "$seen" ]; then
      seen="$nums"
      printf '\a'
      printf '\n[%s] open PR(s) on %s:\n%s\n' "$(date '+%Y-%m-%d %H:%M')" "$REPO" "$prs"
      command -v notify-send >/dev/null 2>&1 && \
        notify-send "AnonShield: open PR(s)" "$prs" 2>/dev/null || true
    fi
  else
    seen=""
  fi
  sleep "$INTERVAL"
done
