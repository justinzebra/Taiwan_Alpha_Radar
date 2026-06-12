#!/usr/bin/env bash
set -euo pipefail

ports=(8000 3000)
found=false
for port in "${ports[@]}"; do
  pids=$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    found=true
    echo "Killing port $port PIDs: $pids"
    kill $pids || true
  fi
done

if [[ "$found" = false ]]; then
  echo "No running frontend/backend process found (maybe already stopped)."
fi

echo "Done."
