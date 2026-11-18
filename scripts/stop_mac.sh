#!/usr/bin/env bash
# Stop and remove the FinAlly container. The data volume is kept.
cd "$(dirname "$0")/.."
docker rm -f finally >/dev/null 2>&1 || true
echo "FinAlly stopped (volume finally-data preserved)."
