#!/bin/bash
# Skrypt do aktywacji venv i instalacji zależności dla obu części projektu

set -e

# Backend (Python - waffen-tactics)
echo "[1/2] Backend: Aktywacja venv i instalacja zależności..."
cd waffen-tactics
if [ ! -d "bot_venv" ]; then
  python3 -m venv bot_venv
fi
source bot_venv/bin/activate
pip install --upgrade pip
if [ -f bot_requirements.txt ]; then
  pip install -r bot_requirements.txt
fi
deactivate
cd ..

# Frontend (Node.js - waffen-tactics-web)
echo "[2/2] Frontend: Instalacja zależności..."
cd waffen-tactics-web
if [ -f package.json ]; then
  npm install
fi
cd ..

echo "Setup zakończony!"
