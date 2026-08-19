#!/bin/zsh
set -euo pipefail

ROOT="/Users/garvsanwariya/bounty/whatsapp_agent"
BACKEND_DIR="$ROOT/wa-saas/backend"

if [ -f "$ROOT/.env" ]; then
  set -a
  source "$ROOT/.env"
  set +a
fi

if [ -f "$BACKEND_DIR/.env" ]; then
  set -a
  source "$BACKEND_DIR/.env"
  set +a
fi

if [ -f "$BACKEND_DIR/.venv/bin/activate" ]; then
  source "$BACKEND_DIR/.venv/bin/activate"
elif [ -f "$BACKEND_DIR/venv/bin/activate" ]; then
  source "$BACKEND_DIR/venv/bin/activate"
elif [ -f "$ROOT/venv/bin/activate" ]; then
  source "$ROOT/venv/bin/activate"
fi

cd "$BACKEND_DIR/app/.."
exec celery -A app.core.celery_app.celery_app beat --loglevel=info
