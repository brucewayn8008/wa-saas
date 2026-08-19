#!/bin/zsh
set -euo pipefail

ROOT="/Users/garvsanwariya/bounty/whatsapp_agent"
FRONTEND_DIR="$ROOT/wa-saas/frontend-next"

cd "$FRONTEND_DIR"
exec npm run dev -- --port 3000
