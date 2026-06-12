#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/stop-local.sh"

echo
echo "Services stopped. Press Enter to close this window."
read -r
