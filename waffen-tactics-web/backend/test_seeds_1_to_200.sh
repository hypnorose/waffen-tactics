#!/bin/bash

# Test seeds 1-200 for desyncs

cd /home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend

PYTHON=../../waffen-tactics/bot_venv/bin/python
START_SEED=1
END_SEED=200
DESYNCS_FOUND=0
FAILED_SEEDS=()

echo "Testing seeds $START_SEED to $END_SEED for desyncs..."
echo ""

for SEED in $(seq $START_SEED $END_SEED); do
    printf "[%3d/%3d] Seed %3d: " $SEED $END_SEED $SEED

    # Generate combat events (suppress debug output)
    $PYTHON save_combat_events.py $SEED events_test_${SEED}.json 2>&1 | grep -q "Saved" || {
        echo "❌ Failed to generate"
        continue
    }

    # Test with frontend replay
    cd ..
    RESULT=$(timeout 10 node test-event-replay.mjs backend/events_test_${SEED}.json 2>&1)
    EXIT_CODE=$?
    cd backend

    if [ $EXIT_CODE -ne 0 ]; then
        if echo "$RESULT" | grep -q "DESYNC DETECTED"; then
            echo "⚠️  DESYNC!"
            echo "$RESULT" | grep -A5 "DESYNC DETECTED" | sed 's/^/     /'
            DESYNCS_FOUND=$((DESYNCS_FOUND + 1))
            FAILED_SEEDS+=($SEED)
        else
            echo "❌ Error"
            echo "$RESULT" | head -3 | sed 's/^/     /'
        fi
    else
        echo "✅"
    fi

    # Clean up to save disk space
    rm -f events_test_${SEED}.json
done

echo ""
echo "========================================"
echo "SUMMARY"
echo "========================================"
echo "Total tests: $((END_SEED - START_SEED + 1))"
echo "Desyncs found: $DESYNCS_FOUND"

if [ $DESYNCS_FOUND -gt 0 ]; then
    echo ""
    echo "Failed seeds: ${FAILED_SEEDS[@]}"
    exit 1
else
    echo "✅ All seeds passed!"
    exit 0
fi
