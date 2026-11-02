#!/usr/bin/env bash
# Start the backend (:8000) and frontend (:3000) together. Ctrl+C stops both.
# The backend does not auto-reload (the reloader hangs on Windows once the embedding
# model is loaded); restart this script after changing Python code.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -x .venv/Scripts/python.exe ]; then PY=.venv/Scripts/python.exe   # Windows (Git Bash)
elif [ -x .venv/bin/python ]; then PY=.venv/bin/python                  # macOS / Linux
else echo "No .venv found. Run: python -m venv .venv && .venv/bin/pip install -r backend/requirements.txt" >&2; exit 1
fi
PY="$(pwd)/$PY"

(cd backend && "$PY" -m uvicorn app.main:app --port 8000) &
BACK=$!
(cd frontend && npm run dev -- --port 3000) &
FRONT=$!

trap 'kill $BACK $FRONT 2>/dev/null' INT TERM EXIT
wait
