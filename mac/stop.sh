#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] Docker not found. If you started with mac/start-local.sh, use mac/stop-local.sh."
  exit 1
fi

echo "Stopping and removing containers ..."
docker compose down

echo
cat <<EOF
Stopped. Database data is kept in the pgdata volume.
To also wipe data, run: docker compose down -v
EOF
