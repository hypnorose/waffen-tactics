#!/bin/bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
WEB_DIR="$PROJECT_ROOT/waffen-tactics-web"
BACKEND_DIR="$WEB_DIR/backend"

echo "Setting up Waffen Tactics web runtime..."

echo "[1/2] Frontend dependencies"
cd "$WEB_DIR"
if [ -f "package-lock.json" ] || [ -f "package.json" ]; then
  npm install
else
  echo "Missing package.json in $WEB_DIR"
  exit 1
fi

echo "[2/2] Backend virtualenv and dependencies"
cd "$BACKEND_DIR"
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo ""
echo "Setup complete."
echo "Copy and fill these files if they are missing:"
echo "  $WEB_DIR/.env.example -> $WEB_DIR/.env"
echo "  $BACKEND_DIR/.env.example -> $BACKEND_DIR/.env"
