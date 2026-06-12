#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] Docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
  echo "Or run mac/start-local.sh instead."
  exit 1
fi

docker info >/dev/null 2>&1 || {
  echo "[ERROR] Docker is installed but not running. Start Docker Desktop and retry."
  exit 1
}

echo "Building and starting containers: db, redis, backend, frontend ..."
docker compose up -d --build

echo "Waiting for backend to finish daily analysis (first run ~10-30s) ..."
tries=0
while ! curl -fsS http://localhost:8000/health >/dev/null 2>&1; do
  tries=$((tries + 1))
  if [[ $tries -ge 120 ]]; then
    echo "[WARN] Backend health check timed out. Containers may still be starting."
    echo "Run docker compose logs -f to inspect, or open http://localhost:3000 later."
    exit 1
  fi
  sleep 2
done

echo "Backend ready!"
open http://localhost:3000
cat <<EOF
  Frontend : http://localhost:3000
  API docs : http://localhost:8000/docs
  To stop: run mac/stop.sh
EOF
