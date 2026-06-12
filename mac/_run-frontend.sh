#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."/frontend || exit 1

if ! command -v node >/dev/null 2>&1; then
  echo "[ERROR] Node.js not found. Install Node 16.14+ from https://nodejs.org/"
  echo "Or use the Docker launcher mac/start.sh instead."
  exit 1
fi

NODEMAJ=$(node -v | sed 's/^v//' | cut -d. -f1)
if [[ -z "$NODEMAJ" || "$NODEMAJ" -lt 16 ]]; then
  echo "[ERROR] Detected Node v$(node -v), but this project needs Node 16.14 or newer."
  echo "Please upgrade Node from https://nodejs.org/ or use Docker start.sh."
  exit 1
fi

if [[ ! -d "node_modules" ]]; then
  echo "Installing frontend packages, first time takes 1-3 minutes ..."
  npm install --legacy-peer-deps
fi

export NEXT_PUBLIC_API_URL="http://localhost:8000/api"
echo "Starting frontend dev server at http://localhost:3000 ..."
echo
npm run dev -- --port 3000

echo
echo "Frontend stopped."
