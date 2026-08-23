#!/usr/bin/env bash
# Demonstrate the error lane: arm the mock so the next 3 mutating Directory calls return 500
# (enough to exhaust the create node's 3 retries), then fire a fresh HRIS event.
# After you click Approve, the execution fails at "Google: create user" and #it-alerts gets a message.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$ROOT/.env" ]; then set -a; . "$ROOT/.env"; set +a; fi
MOCK="${GOOGLE_ADMIN_BASE_URL:-http://localhost:8000}"   # host-side address of the mock

curl -sS -X POST "$MOCK/_mock/reset" >/dev/null
curl -sS -X POST "$MOCK/_mock/fail-next" -H 'Content-Type: application/json' -d '{"count":3,"status":500}'
echo
"$ROOT/scripts/fire-webhook.sh"
