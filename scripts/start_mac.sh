#!/usr/bin/env bash
# Start FinAlly (idempotent). Usage: start_mac.sh [--build] [--open]
set -euo pipefail
cd "$(dirname "$0")/.."
BUILD=0; OPEN=0
for a in "$@"; do case "$a" in --build) BUILD=1;; --open) OPEN=1;; esac; done

if [ ! -f .env ]; then
  if [ -f .env.example ]; then cp .env.example .env; echo "Created .env from .env.example (edit it to set OPENROUTER_API_KEY)."
  else touch .env; fi
fi

if [ "$BUILD" = 1 ] || ! docker image inspect finally >/dev/null 2>&1; then
  echo "Building image..."
  docker build -t finally .
fi

docker rm -f finally >/dev/null 2>&1 || true
docker run -d --name finally -v finally-data:/app/db -p 8000:8000 --env-file .env finally >/dev/null

URL="http://localhost:8000"
echo "FinAlly is running at $URL"
if [ "$OPEN" = 1 ]; then
  (open "$URL" 2>/dev/null || xdg-open "$URL" 2>/dev/null) || true
fi
