# Desync Debugging Tools

## Overview

This directory contains tools to debug combat event desync issues between the backend simulator and frontend replay.

## Quick Start

### Test the Tools

```bash
cd waffen-tactics-web/backend
./test_debug_tools.sh
```

### Debug a Combat

```bash
# Test with a specific seed
python3 debug_desync.py --seed 42

# Analyze missing events
python3 debug_desync.py --seed 42 --analyze-missing

# Test saved events from a file
python3 debug_desync.py events_combat.json
```

### Example Output

```
================================================================================
SUMMARY
================================================================================
Total events: 247
Effect events emitted:
  unit_stunned: 12
  stat_buff: 25
  shield_applied: 8
  damage_over_time_applied: 6
Desyncs detected: 0

✅ No desyncs detected! All events replay correctly.
```

If there ARE desyncs:

```
================================================================================
DESYNC DETECTED at seq=137 (event index 45)
================================================================================
Event type: mana_update
Error: Effects mismatch for player unit 8d6d21ac at seq 137 (seed 42):
       reconstructed=[], snapshot=[('stun', None, None, None, 'source123', 0.6)]

⚠️  Missing unit_stunned event for 8d6d21ac (effect_id=abc-123)
    Snapshot seq=140, timestamp=1.4
    Effect details: {"type":"stun","duration":1.5,"source":"opp_2"}
```

## Files

- **`debug_desync.py`** - Main debugging script
- **`test_debug_tools.sh`** - Validation test script
- **`DEBUGGING_EXAMPLE.md`** - Quick start examples
- **`combat_event_reconstructor.py`** - Event replay validator

## Full Documentation

See the root directory for complete guides:

- **[EVENT_REPLAY_TESTING.md](../../docs/EVENT_REPLAY_TESTING.md)** - Canonical replay and desync-testing guide
- **[COMBAT_RUNTIME_BOUNDARY.md](../../docs/COMBAT_RUNTIME_BOUNDARY.md)** - Runtime ownership boundary
- **[RELEASE_VALIDATION_GATE.md](../../docs/RELEASE_VALIDATION_GATE.md)** - Release validation contract

## Frontend Tools

The frontend also has event logging available in the browser console:

```javascript
// After a combat finishes:
eventLogger.printSummary()
eventLogger.getEventsByType('unit_stunned')
event Logger.downloadLog('combat_events.json')
```

See the full guide for details on coordinating backend and frontend debugging.
