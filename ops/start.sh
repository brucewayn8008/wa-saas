#!/bin/zsh
set -euo pipefail

ROOT="/Users/garvsanwariya/bounty/whatsapp_agent"
BACKEND_DIR="$ROOT/wa-saas/backend"
GATEWAY_DIR="$ROOT/wa-saas/go-gateway"
FRONTEND_DIR="$ROOT/wa-saas/frontend-next"
LANDING_DIR="$ROOT/whatsapp_landing"
VENV_DIR="${VIRTUAL_ENV:-$BACKEND_DIR/.venv}"
LOG_DIR="$ROOT/wa-saas/ops/logs"
mkdir -p "$LOG_DIR"

grn() { printf '\033[0;32m%s\033[0m\n' "$1"; }
ylw() { printf '\033[0;33m%s\033[0m\n' "$1"; }
red() { printf '\033[0;31m%s\033[0m\n' "$1"; }

# ── preflight ──────────────────────────────────────────────
# 1) PostgreSQL
if pg_isready -q 2>/dev/null; then
  grn "✔ PostgreSQL running"
else
  ylw "▶ Starting PostgreSQL…"
  pg_ctl -D /opt/homebrew/var/postgres start 2>/dev/null || brew services start postgresql || true
fi

# 2) Redis
if redis-cli ping 2>/dev/null | grep -q PONG; then
  grn "✔ Redis running"
else
  ylw "▶ Starting Redis…"
  redis-server --daemonize yes 2>/dev/null || brew services start redis || true
fi

# 3) Load env
if [ -f "$ROOT/.env" ]; then
  set -a; source "$ROOT/.env"; set +a
fi
if [ -f "$BACKEND_DIR/.env" ]; then
  set -a; source "$BACKEND_DIR/.env"; set +a
fi

# ── kill stale ports ────────────────────────────────────────
for port in 8000 5001 5005 3000 3001 3002; do
  pid=$(lsof -ti tcp:$port 2>/dev/null) && kill -9 $pid 2>/dev/null || true
done
sleep 0.5

# ── start services ────────────────────────────────────────
grn "▶ B2B Backend (uvicorn :8000)"
cd "$BACKEND_DIR/app/.."
source "$VENV_DIR/bin/activate" 2>/dev/null || true
uvicorn app.main:app --host 127.0.0.1 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
echo $! > "$LOG_DIR/backend.pid"

grn "▶ B2B Celery worker"
cd "$BACKEND_DIR/app/.."
celery -A app.core.celery_app.celery_app worker --loglevel=info > "$LOG_DIR/worker.log" 2>&1 &
echo $! > "$LOG_DIR/worker.pid"

grn "▶ B2B Celery beat"
cd "$BACKEND_DIR/app/.."
celery -A app.core.celery_app.celery_app beat --loglevel=info > "$LOG_DIR/beat.log" 2>&1 &
echo $! > "$LOG_DIR/beat.pid"

sleep 2

grn "▶ Go WhatsApp gateway (:5005)"
export WEBHOOK_URL="http://127.0.0.1:8000/api/v1/webhook/message"
cd "$GATEWAY_DIR"
go run main.go > "$LOG_DIR/gateway.log" 2>&1 &
echo $! > "$LOG_DIR/gateway.pid"

sleep 2

if [ -d "$FRONTEND_DIR" ]; then
  grn "▶ Sales Agent Next.js frontend (:3000)"
  cd "$FRONTEND_DIR"
  npm run dev -- --port 3000 > "$LOG_DIR/frontend.log" 2>&1 &
  echo $! > "$LOG_DIR/frontend.pid"
fi

if [ -d "$LANDING_DIR" ]; then
  grn "▶ Landing page (:3001)"
  cd "$LANDING_DIR"
  npm run dev -- --port 3001 > "$LOG_DIR/landing.log" 2>&1 &
  echo $! > "$LOG_DIR/landing.pid"
fi

sleep 2

echo ""
grn "═══════════════════════════════════════════"
grn "  All sales agent services started"
grn "  Sales Backend    : http://127.0.0.1:8000"
grn "  Go Gateway       : http://127.0.0.1:5005"
grn "  Sales Frontend   : http://localhost:3000"
grn "  Landing Page     : http://localhost:3001"
grn "  Logs             : $LOG_DIR"
grn "═══════════════════════════════════════════"
echo ""
echo "Press Ctrl-C to stop all services."

# ── graceful shutdown ──────────────────────────────────────
trap 'ylw "Stopping…"; for f in "$LOG_DIR"/*.pid; do [ -f "$f" ] && kill $(cat "$f") 2>/dev/null || true; done; exit 0' INT TERM

wait
