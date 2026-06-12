#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."/backend || exit 1

if [[ ! -x ".venv/bin/python" ]]; then
  echo "[ERROR] Virtual env not found. Run mac/start-local.sh first."
  exit 1
fi

source .venv/bin/activate

export DATABASE_URL="sqlite:///./taiwan_alpha_radar.db"
export REDIS_URL="redis://localhost:6379/0"
export AI_PROVIDER="mock"
export DATA_PROVIDER="official_close"
export MARKET_HISTORY_DAYS="180"
export PREDICTION_LOOKBACK_DAYS="120"
export CORS_ORIGINS="http://localhost:3000"
export AUTO_SEED_ON_STARTUP="true"
export ENABLE_SCHEDULER="true"

echo "Starting backend (SQLite) with official TWSE/TPEx close data."
echo "First boot downloads historical data and may take a few minutes."
echo "Wait for the line \"Pipeline complete\" - that means analysis is done."
echo
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo
echo "Backend stopped."
