#!/usr/bin/env bash
set -euo pipefail

CONSOLE_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$CONSOLE_DIR/.venv"
PID_FILE="$CONSOLE_DIR/.console.pid"

# --- Kill any running console instance ---
if [[ -f "$PID_FILE" ]]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Stopping existing console (PID $OLD_PID)..."
    kill "$OLD_PID"
    for i in {1..10}; do
      kill -0 "$OLD_PID" 2>/dev/null || break
      sleep 0.5
    done
    if kill -0 "$OLD_PID" 2>/dev/null; then
      echo "Force killing PID $OLD_PID..."
      kill -9 "$OLD_PID"
    fi
  fi
  rm -f "$PID_FILE"
fi

# --- Create venv if it doesn't exist ---
if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

# --- Install/update dependencies if needed ---
MARKER="$VENV_DIR/.installed"
REQUIREMENTS="$CONSOLE_DIR/requirements.txt"

if [[ ! -f "$MARKER" || "$REQUIREMENTS" -nt "$MARKER" ]]; then
  echo "Installing dependencies..."
  "$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip
  "$VENV_DIR/bin/python" -m pip install --quiet -r "$REQUIREMENTS"
  touch "$MARKER"
fi

# --- Start console ---
PORT="${PORT:-8080}"
MCP_URL="${MCP_URL:-http://localhost:9030/mcp}"

echo "Starting console (port: $PORT, MCP_URL: $MCP_URL)..."
MCP_URL="$MCP_URL" "$VENV_DIR/bin/python" -m uvicorn app:app \
  --host "${HOST:-0.0.0.0}" \
  --port "$PORT" \
  --app-dir "$CONSOLE_DIR" &

CONSOLE_PID=$!
echo "$CONSOLE_PID" > "$PID_FILE"
echo "Console started (PID $CONSOLE_PID). PID saved to $PID_FILE"

wait "$CONSOLE_PID"
rm -f "$PID_FILE"
