#!/bin/zsh
set -euo pipefail

ROOT="/Users/garvsanwariya/bounty/whatsapp_agent"
GATEWAY_DIR="$ROOT/wa-saas/go-gateway"

if [ -f "$ROOT/.env" ]; then
  set -a
  source "$ROOT/.env"
  set +a
fi

if [ -f "$ROOT/wa-saas/backend/.env" ]; then
  set -a
  source "$ROOT/wa-saas/backend/.env"
  set +a
fi

export DB_HOST="${POSTGRES_SERVER:-localhost}"
export DB_PORT="${POSTGRES_PORT:-5432}"
export DB_USER="${POSTGRES_USER:-postgres}"
export DB_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
export DB_NAME="${POSTGRES_DB:-wa_saas}"
export WEBHOOK_URL="${WEBHOOK_URL:-http://127.0.0.1:8000/api/v1/webhook/message}"
export GATEWAY_PORT="${GATEWAY_PORT:-5005}"

cd "$GATEWAY_DIR"
exec go run main.go
