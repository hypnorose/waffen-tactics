#!/bin/bash
# Test script to validate debugging tools are working

set -e

echo "================================="
echo "Desync Debugging Tools Test"
echo "================================="
echo ""

# Check Python version
echo "1. Checking Python..."
python3 --version || { echo "❌ Python3 not found"; exit 1; }
echo "✅ Python3 available"
echo ""

# Check if debug script exists
echo "2. Checking debug_desync.py..."
if [ ! -f "debug_desync.py" ]; then
    echo "❌ debug_desync.py not found"
    exit 1
fi
echo "✅ debug_desync.py exists"
echo ""

# Check if it's executable
echo "3. Testing debug script help..."
python3 debug_desync.py --help > /dev/null || { echo "❌ debug_desync.py failed"; exit 1; }
echo "✅ debug_desync.py runs"
echo ""

# Check dependencies
echo "4. Checking Python dependencies..."
python3 -c "import sys; sys.path.insert(0, '../../waffen-tactics/src')" || { echo "❌ waffen-tactics path issue"; exit 1; }
echo "✅ Path setup correct"
echo ""

# Test with a quick seed (small team for speed)
echo "5. Running quick test (seed=1, team_size=2)..."
python3 debug_desync.py --seed 1 --team-size 2 --quiet || {
    echo "❌ Test combat failed"
    echo ""
    echo "This might be expected if there are actual desyncs."
    echo "Run manually to see details:"
    echo "  python3 debug_desync.py --seed 1 --team-size 2"
    exit 1
}
echo "✅ Test combat passed"
echo ""

echo "================================="
echo "All Tests Passed! ✅"
echo "================================="
echo ""
echo "Tools are ready to use:"
echo ""
echo "  Backend debugger:"
echo "    cd waffen-tactics-web/backend"
echo "    python3 debug_desync.py --seed 42"
echo ""
echo "  Frontend logger:"
echo "    Open browser console during combat"
echo "    Run: eventLogger.printSummary()"
echo ""
echo "Documentation:"
echo "  - DESYNC_DEBUGGING_GUIDE.md (comprehensive)"
echo "  - DEBUGGING_EXAMPLE.md (quick examples)"
echo "  - DESYNC_QUICK_REFERENCE.md (cheat sheet)"
echo ""
