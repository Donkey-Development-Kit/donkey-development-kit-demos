#!/usr/bin/env bash
# One-command boot for the DDK Feature Showcase.
#
#   ./run.sh          build the frontend, serve everything from the backend on :8000
#   ./run.sh --dev    run the backend on :8000 and the Vite dev server on :5173
#
# The backend spawns `donkey mock` itself (see app/simulator.py) — no separate
# gateway, no credentials, no OpenAI key required.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEV="${1:-}"

echo "==> Installing backend deps"
python3 -m pip install -q -r "$ROOT/backend/requirements.txt"

if [[ "$DEV" == "--dev" ]]; then
  echo "==> Dev mode: backend :8000 + Vite dev server :5173"
  ( cd "$ROOT/frontend" && npm install )
  ( cd "$ROOT/backend" && PYTHONPATH=. python3 -m uvicorn app.main:app --port 8000 --reload ) &
  BACKEND_PID=$!
  trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT
  cd "$ROOT/frontend" && npm run dev
else
  echo "==> Building frontend"
  ( cd "$ROOT/frontend" && npm install && npm run build )
  echo "==> Serving demo on http://127.0.0.1:8000"
  cd "$ROOT/backend" && PYTHONPATH=. python3 -m uvicorn app.main:app --port 8000
fi
