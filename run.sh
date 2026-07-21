#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="$(dirname "$0")/.venv"
PID_FILE="$(dirname "$0")/.server.pid"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Kill any running server instance ---
if [[ -f "$PID_FILE" ]]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Stopping existing server (PID $OLD_PID)..."
    kill "$OLD_PID"
    # Wait up to 5 seconds for it to stop
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
PYPROJECT="$SCRIPT_DIR/pyproject.toml"

if [[ ! -f "$MARKER" || "$PYPROJECT" -nt "$MARKER" ]]; then
  echo "Installing dependencies..."
  "$VENV_DIR/bin/pip" install --quiet --upgrade pip
  "$VENV_DIR/bin/pip" install --quiet -e "$SCRIPT_DIR[console]"
  touch "$MARKER"
fi

# --- Start server ---
echo "Starting openfinance-mcp server (transport: ${TRANSPORT:-http}, port: ${PORT:-9030})..."
"$VENV_DIR/bin/openfinance-mcp" \
  --transport "${TRANSPORT:-http}" \
  --host "${HOST:-0.0.0.0}" \
  --port "${PORT:-9030}" &

SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"
echo "Server started (PID $SERVER_PID). PID saved to $PID_FILE"

wait "$SERVER_PID"
rm -f "$PID_FILE"
