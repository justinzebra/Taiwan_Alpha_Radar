#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! "$SCRIPT_DIR/start-local.sh"; then
  echo
  echo "Startup failed. Press Enter to close this window."
  read -r
  exit 1
fi
