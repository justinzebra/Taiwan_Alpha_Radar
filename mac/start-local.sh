#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

if [[ -f "$HOME/.local/bin/env" ]]; then
  source "$HOME/.local/bin/env"
fi

PYTHON_BIN=""
for candidate in python3.12 python3.11 python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
      PYTHON_BIN="$candidate"
      break
    fi
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  echo "[ERROR] Python not found. Install Python 3.11+ from https://www.python.org/"
  exit 1
fi

if [[ ! -x "backend/.venv/bin/python" ]]; then
  echo "[Backend] Creating virtual env backend/.venv ..."
  "$PYTHON_BIN" -m venv backend/.venv
  backend/.venv/bin/python -m pip install --upgrade pip
  backend/.venv/bin/python -m pip install -r backend/requirements.txt
fi

if curl -fsS http://localhost:3000 >/dev/null 2>&1 &&
   curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
  echo "[INFO] Local services are already running."
  echo "Opening http://localhost:3000 ..."
  open http://localhost:3000
  exit 0
fi

if lsof -tiTCP:3000 -sTCP:LISTEN >/dev/null 2>&1 ||
   lsof -tiTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[INFO] Found an incomplete previous startup. Cleaning it up ..."
  ./mac/stop-local.sh
  sleep 1
fi

echo
if command -v osascript >/dev/null 2>&1; then
  echo "Opening two Terminal windows for backend and frontend ..."
  osascript <<EOF
tell application "Terminal"
  do script "cd '$REPO_DIR' && ./mac/_run-backend.sh"
  do script "cd '$REPO_DIR' && ./mac/_run-frontend.sh"
end tell
EOF
else
  echo "[WARN] osascript unavailable. Running services in the current shell instead."
  ./mac/_run-backend.sh &
  ./mac/_run-frontend.sh &
fi

echo "Waiting for backend to be ready ..."
tries=0
while ! curl -fsS http://localhost:8000/health >/dev/null 2>&1; do
  tries=$((tries + 1))
  if [[ $tries -ge 60 ]]; then
    echo "[WARN] Backend did not respond within 120 seconds."
    break
  fi
  sleep 2
done

echo "Opening browser ..."
open http://localhost:3000

echo
cat <<EOF
  Backend should be available at http://localhost:8000/docs
  Frontend should be available at http://localhost:3000
  To stop: run mac/stop-local.sh
EOF
