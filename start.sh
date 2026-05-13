#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== myFinance Setup ==="

# ── Backend ───────────────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/backend"

if [ ! -f "../.env" ]; then
  cp ../.env.example ../.env
  echo "Created .env from .env.example — add your API keys there."
fi

if [ ! -d "venv" ]; then
  echo "Creating Python virtualenv (requires Python 3.13)..."
  # Use python3.13 explicitly — Python 3.14 lacks prebuilt wheels for Rust extensions
  PYTHON_BIN=$(which python3.13 2>/dev/null || echo "")
  if [ -z "$PYTHON_BIN" ]; then
    echo "ERROR: Python 3.13 not found. Install it with: brew install python@3.13"
    exit 1
  fi
  "$PYTHON_BIN" -m venv venv
fi

echo "Installing backend dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

echo "Starting backend on http://localhost:8000 ..."
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# ── Frontend ──────────────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/frontend"

if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

echo "Starting frontend on http://localhost:5173 ..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✓ Backend:  http://localhost:8000"
echo "✓ Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers."

# Wait and cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
