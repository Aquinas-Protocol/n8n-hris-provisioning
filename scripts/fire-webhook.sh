#!/usr/bin/env bash
# Fire one mock HRIS "employee.hired" event at the published workflow's webhook.
# Uses samples/new-hire.local.json if you made one (gitignored), else samples/new-hire.json.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$ROOT/.env" ]; then set -a; . "$ROOT/.env"; set +a; fi

cd "$ROOT"   # relative payload path: immune to MSYS path-conversion quirks on Git Bash
PAYLOAD="samples/new-hire.local.json"
[ -f "$PAYLOAD" ] || PAYLOAD="samples/new-hire.json"
BASE="${WEBHOOK_URL:-http://localhost:5678/}"
URL="${BASE%/}/webhook/hris/new-hire"

echo "POST $URL  ($(basename "$PAYLOAD"))"
curl -sS -X POST "$URL" \
  -H "Content-Type: application/json" \
  -H "X-HRIS-Token: ${HRIS_WEBHOOK_TOKEN:?set HRIS_WEBHOOK_TOKEN in .env}" \
  --data-binary @"$PAYLOAD"
echo
