#!/bin/sh
set -eu

ROOT="/Users/juntae.park/projects/harness-platform"
BACKEND_DIR="$ROOT/harness-os/backend"
FRONTEND_DIR="$ROOT/harness-os/frontend"
VENV="$ROOT/.venv/bin/activate"
LOG_DIR="$ROOT/logs"

mkdir -p "$LOG_DIR"

if ! lsof -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  (
    cd "$BACKEND_DIR"
    # shellcheck disable=SC1090
    . "$VENV"
    nohup uvicorn main:app --host 127.0.0.1 --port 8000 >>"$LOG_DIR/harness-os-backend.log" 2>&1 &
  )
fi

if ! lsof -iTCP:5173 -sTCP:LISTEN >/dev/null 2>&1; then
  (
    cd "$FRONTEND_DIR"
    nohup npm run dev -- --host 127.0.0.1 --port 5173 --strictPort >>"$LOG_DIR/harness-os-frontend.log" 2>&1 &
  )
fi

echo "Harness-OS local services started (or already running)."
