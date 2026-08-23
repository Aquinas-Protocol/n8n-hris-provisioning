#!/usr/bin/env bash
# Import (upsert) both workflows into n8n, then list them. Add --publish to publish the main
# workflow from the CLI and restart n8n so the production webhook goes live.
# Works against the compose stack if it is running, otherwise against a native n8n (npx).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if docker compose ps --status running --services 2>/dev/null | grep -qx n8n; then
  N8N=(docker compose exec -T n8n n8n)
  INPUT=/workflows                      # read-only bind mount, see docker-compose.yml
else
  N8N=(npx -y n8n@2.35.7)
  INPUT="$ROOT/workflows"
fi

"${N8N[@]}" import:workflow --separate --input="$INPUT"
"${N8N[@]}" list:workflow

if [ "${1:-}" = "--publish" ]; then
  "${N8N[@]}" publish:workflow --id=HRISPROVMAIN0001
  if [ "${N8N[0]}" = docker ]; then docker compose restart n8n; else echo "restart your native n8n to activate the webhook"; fi
fi
