#!/usr/bin/env bash
# Native (no Docker) run: the mock Admin SDK in the background + n8n 2.35.7 via npx in the foreground.
# Needs Node 20.19–24.x and Python 3.11+. Data lands in ~/.n8n. Ctrl-C stops both.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$ROOT/.env" ]; then set -a; . "$ROOT/.env"; set +a; fi
export N8N_BLOCK_ENV_ACCESS_IN_NODE=false
export GOOGLE_ADMIN_BASE_URL="${GOOGLE_ADMIN_BASE_URL:-http://localhost:8000}"
export WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:5678/}"
export N8N_DIAGNOSTICS_ENABLED=false N8N_VERSION_NOTIFICATIONS_ENABLED=false N8N_PERSONALIZATION_ENABLED=false

python "$ROOT/mock-google-admin/mock_google_admin.py" --port 8000 &
MOCK_PID=$!
trap 'kill $MOCK_PID 2>/dev/null || true' EXIT
npx -y n8n@2.35.7
