#!/bin/bash

# Test multiple random seeds for desyncs

cd /home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend

PYTHON=../../waffen-tactics/bot_venv/bin/python
TOTAL_TESTS=20
DESYNCS_FOUND=0

echo "Testing $TOTAL_TESTS random combat scenarios..."
echo ""

for i in $(seq 1 $TOTAL_TESTS); do
    SEED=$((1000 + i * 137))  # Pseudo-random but reproducible

    echo "[$i/$TOTAL_TESTS] Testing seed $SEED..."

    # Generate combat events
    $PYTHON save_combat_events.py $SEED events_test_${SEED}.json 2>&1 | grep -q "Saved" || {
        echo "  ❌ Failed to generate events"
        continue
    }

    # Test with frontend replay
    cd ..
    RESULT=$(node test-event-replay.mjs backend/events_test_${SEED}.json 2>&1)
    cd backend

    if echo "$RESULT" | grep -q "DESYNC DETECTED"; then
        echo "  ⚠️  DESYNC FOUND!"
        echo "$RESULT" | grep -A3 "DESYNC DETECTED"
        DESYNCS_FOUND=$((DESYNCS_FOUND + 1))
    elif echo "$RESULT" | grep -q "SUCCESS"; then
        echo "  ✅ Pass"
    else
        echo "  ❌ Error"
        echo "$RESULT" | head -5
    fi
done

echo ""
echo "================================"
echo "SUMMARY: $DESYNCS_FOUND desyncs found in $TOTAL_TESTS tests"
echo "================================"
