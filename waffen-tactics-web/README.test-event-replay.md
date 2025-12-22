# Event Replay Testing

Quick reference for validating combat event streams against frontend logic.

## Quick Start

```bash
# Test with an existing event stream
node test-event-replay.mjs <path-to-events.json>

# Example: Test with desync logs
node test-event-replay.mjs ../desync_logs_1766289011979.json
```

## What It Does

- Loads combat event stream (JSON)
- Applies each event using **actual frontend `applyEvent` logic**
- Compares UI state vs backend `game_state` at each snapshot
- Reports desyncs with detailed diffs (unit, stat, UI value, server value)

## Exit Codes

- `0`: All events applied correctly, no desyncs
- `1`: Desyncs detected OR error occurred

## Example Output

### ✅ Success
```
================================================================================
VALIDATING EVENT STREAM
================================================================================

Total events: 200

================================================================================
VALIDATION SUMMARY
================================================================================

✅ SUCCESS: No desyncs detected!
   All 200 events applied correctly.

================================================================================
```

### ❌ Failure
```
⚠️  DESYNC DETECTED at event #145 (seq=167, t=14.50s)
   Unit: Streamer (player_2)
      attack: UI=125 vs Server=135
      defense: UI=25 vs Server=30

================================================================================
VALIDATION SUMMARY
================================================================================

❌ FAILED: 2 desyncs across 1 snapshots

   Desyncs by snapshot:
      Event #145 (seq=167, t=14.50s): 1 unit(s)

================================================================================
```

## Event Stream Format

Accepts both:

**JSON Array:**
```json
[
  {"type": "start", "seq": 1, "timestamp": 0.0},
  {"type": "state_snapshot", "seq": 10, "game_state": {...}}
]
```

**JSONL (one event per line):**
```jsonl
{"type": "start", "seq": 1, "timestamp": 0.0}
{"type": "state_snapshot", "seq": 10, "game_state": {...}}
```

## Requirements

- Node.js 18+ (uses ES modules)
- Event stream must include `state_snapshot` events with `game_state` field

## See Also

- Full documentation: [`docs/EVENT_REPLAY_TESTING.md`](../docs/EVENT_REPLAY_TESTING.md)
- Frontend event handler: [`src/hooks/combat/applyEvent.ts`](src/hooks/combat/applyEvent.ts)
- Desync detection: [`src/hooks/combat/desync.ts`](src/hooks/combat/desync.ts)
