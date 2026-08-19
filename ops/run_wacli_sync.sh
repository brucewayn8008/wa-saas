#!/bin/zsh
# Run wacli sync --follow with a signed webhook into the SaaS API (Feature 06).
#
# Usage:
#   ./ops/run_wacli_sync.sh
#   ACCOUNT=tenant-a WORKSPACE_ID=<uuid> ./ops/run_wacli_sync.sh
#
# Prerequisites:
#   - wacli installed and authenticated (`wacli auth` / QR) for this store
#   - backend listening (default http://127.0.0.1:8000)
#   - WACLI_WEBHOOK_SECRET set in env or backend/.env

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT/backend"

if [ -f "$BACKEND_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$BACKEND_DIR/.env"
  set +a
fi

WACLI_BIN="${WACLI_BIN:-wacli}"
WACLI_STORE_DIR="${WACLI_STORE_DIR:-$HOME/.wacli}"
WACLI_WEBHOOK_SECRET="${WACLI_WEBHOOK_SECRET:-}"
API_BASE="${API_BASE:-http://127.0.0.1:8000}"
ACCOUNT="${ACCOUNT:-${WACLI_ACCOUNT:-}}"
WORKSPACE_ID="${WORKSPACE_ID:-}"

if [ -z "$WACLI_WEBHOOK_SECRET" ]; then
  echo "error: WACLI_WEBHOOK_SECRET is required" >&2
  exit 1
fi

WEBHOOK_URL="${API_BASE%/}/api/v1/webhook/wacli"
QS=()
if [ -n "$ACCOUNT" ]; then
  QS+=("account=${ACCOUNT}")
fi
if [ -n "$WORKSPACE_ID" ]; then
  QS+=("workspace_id=${WORKSPACE_ID}")
fi
if [ ${#QS[@]} -gt 0 ]; then
  WEBHOOK_URL="${WEBHOOK_URL}?$(IFS='&'; echo "${QS[*]}")"
fi

STORE="$WACLI_STORE_DIR"
if [ -n "$ACCOUNT" ]; then
  STORE="${WACLI_STORE_DIR%/}/accounts/${ACCOUNT}"
fi

echo "▶ wacli sync --follow"
echo "  store:   $STORE"
echo "  webhook: $WEBHOOK_URL"

exec "$WACLI_BIN" --store "$STORE" sync --follow \
  --webhook "$WEBHOOK_URL" \
  --webhook-secret "$WACLI_WEBHOOK_SECRET" \
  --webhook-events message,receipt,chat_presence
