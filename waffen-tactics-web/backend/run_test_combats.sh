#!/bin/bash
# Run test combats with specific team compositions using existing backend

echo "Running test combat scenarios..."

# Use pytest to run specific seed tests
cd /home/ubuntu/waffen-tactics-game/waffen-tactics

# Run with different seeds to get variety
for seed in 100 200 300 400 500; do
  echo "Running combat with seed $seed..."
  timeout 30 ./bot_venv/bin/python -m pytest tests/test_combat.py::test_basic_combat -v --tb=short -s 2>&1 | head -50
done

echo "Test combats completed. Check backend/events_*.json for results"
