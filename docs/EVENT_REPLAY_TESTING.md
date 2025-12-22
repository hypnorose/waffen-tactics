# Event Replay Testing Guide

## Overview

This testing system validates that the **frontend `applyEvent` logic** correctly reconstructs combat state from backend event streams. Unlike the Python-based `CombatEventReconstructor`, this tests the **actual production TypeScript code** that runs in the browser.

## Why This Approach is Superior

1. **Tests Real Frontend Logic**: Uses your actual `applyEvent.ts` implementation, not a Python simulation
2. **Catches Frontend-Specific Bugs**: Issues with TypeScript type coercion, state immutability, or React-specific logic
3. **E2E Validation**: Verifies the entire pipeline from backend → SSE → frontend → state application
4. **Easier Debugging**: Step through the exact code that users experience in production

## How It Works

```
Backend Combat Simulation (Python)
  ↓ Emits events with game_state snapshots
  ↓ Saved to JSON file
  ↓
Node.js Test Harness (test-event-replay.mjs)
  ↓ Loads event stream
  ↓ Applies each event using applyCombatEvent() (actual frontend code)
  ↓ Compares UI state vs server game_state at each snapshot
  ↓ Reports desyncs with detailed diffs
```

## Files

### Test Harness
- **`waffen-tactics-web/test-event-replay.mjs`**: Node.js script that replays events and validates state
  - Inlines the `applyEvent` logic from `src/hooks/combat/applyEvent.ts`
  - Implements state comparison from `src/hooks/combat/desync.ts`
  - Reports desyncs with unit-level diffs

### Event Stream Generator
- **`waffen-tactics-web/backend/save_combat_events.py`**: Python script to save combat events to JSON
  - Runs a combat simulation with event callbacks
  - Saves all events (including `game_state` snapshots) to JSON
  - Currently requires fixing to work with current game architecture

## Usage

### 1. Save Combat Event Stream (Backend)

**From existing game combat** (recommended for now):

The backend already emits events during combat. To capture them:

```bash
# Option A: Use existing desync logs
cd waffen-tactics-game
ls desync_logs_*.json  # Find existing event streams
```

**From test combat** (future - requires fixing `save_combat_events.py`):

```bash
cd waffen-tactics-web/backend

# Generate with specific seed
python3 save_combat_events.py 5 events_seed5.json

# Generate with random seed
python3 save_combat_events.py --random events_random.json
```

### 2. Validate Event Stream (Frontend)

```bash
cd waffen-tactics-web

# Test with saved event stream
node test-event-replay.mjs <path-to-events.json>

# Example
node test-event-replay.mjs ../desync_logs_1766289011979.json
node test-event-replay.mjs backend/logs/failing-seeds/seed_205.json
```

### 3. Interpret Results

**Success Output:**
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

**Failure Output:**
```
================================================================================
VALIDATING EVENT STREAM
================================================================================

Total events: 3

⚠️  DESYNC DETECTED at event #2 (seq=3, t=1.00s)
   Unit: Test Unit (player_0)
      current_mana: UI=0 vs Server=10
   Unit: Enemy Unit (opp_0)
      hp: UI=60 vs Server=65

================================================================================
VALIDATION SUMMARY
================================================================================

❌ FAILED: 2 desyncs across 1 snapshots

   Desyncs by snapshot:
      Event #2 (seq=3, t=1.00s): 2 unit(s)

================================================================================
```

## Event Stream Format

The test harness accepts:

1. **JSON Array** (one array containing all events):
```json
[
  {"type": "start", "seq": 1, "timestamp": 0.0},
  {"type": "units_init", "seq": 2, "player_units": [...], ...},
  {"type": "state_snapshot", "seq": 10, "game_state": {...}, ...}
]
```

2. **JSONL** (one event per line):
```jsonl
{"type": "start", "seq": 1, "timestamp": 0.0}
{"type": "units_init", "seq": 2, "player_units": [...], ...}
{"type": "state_snapshot", "seq": 10, "game_state": {...}, ...}
```

### Required Fields

Each event must have:
- `type`: Event type (e.g., "unit_attack", "mana_update", "stat_buff")
- `seq`: Sequence number (for ordering)
- `timestamp`: Simulation time in seconds

State snapshot events must additionally have:
- `game_state`: Object with `player_units` and `opponent_units` arrays

## Debugging Desyncs

When desyncs are detected:

### 1. Identify the Event Type
Look at the event index and timestamp:
```
⚠️  DESYNC DETECTED at event #2 (seq=3, t=1.00s)
```

### 2. Check Which Stats Diverged
```
   Unit: Enemy Unit (opp_0)
      hp: UI=60 vs Server=65
```

This tells you:
- **Which unit** has the problem (`opp_0`)
- **Which stat** is wrong (`hp`)
- **How much** it diverged (UI calculated `60`, server says `65`)

### 3. Find the Root Cause

Common causes:
- **Missing authoritative HP field**: Event should include `unit_hp` or `post_hp`, but frontend fell back to delta calculation
- **Incorrect delta calculation**: Frontend calculated damage/heal differently than backend
- **Missing event**: Backend emitted an event that wasn't applied by frontend
- **Wrong event order**: Events applied out of sequence
- **Effect application bug**: Buffs/debuffs/DoTs applied incorrectly

### 4. Fix the Bug

**Backend fix** (event emission):
```python
# BAD: Missing authoritative HP
self.emit_attack(attacker, target, damage)

# GOOD: Include post-attack HP
self.emit_attack(attacker, target, damage, target_hp=target.hp)
```

**Frontend fix** (event application):
```typescript
// BAD: Delta calculation (unreliable)
const newHp = u.hp - event.damage

// GOOD: Use authoritative HP from backend
const newHp = event.unit_hp ?? (u.hp - event.damage)  // Fallback for old events
```

## Comparison with Python Reconstructor

| Feature | Node.js Replay Test | Python Reconstructor |
|---------|-------------------|---------------------|
| **Code tested** | Actual frontend `applyEvent.ts` | Python simulation of frontend logic |
| **Language** | TypeScript/JavaScript | Python |
| **Catches** | All frontend bugs | Only logic bugs (not type coercion, etc.) |
| **False positives** | Fewer (tests real code) | More (Python ≠ TypeScript) |
| **Speed** | Fast (Node.js) | Fast (Python) |
| **Integration** | Can import from `src/` | Separate reimplementation |

**Recommendation**: Use **both** systems:
- Python reconstructor during backend development (faster iteration)
- Node.js replay test for final validation (tests production code)

## Future Improvements

### 1. Direct TypeScript Import
Instead of inlining `applyEvent` logic, import the actual TS file:

```javascript
// With tsx or ts-node
import { applyCombatEvent } from './src/hooks/combat/applyEvent.ts'
```

Benefits:
- No code duplication
- Automatic updates when frontend changes
- Same TypeScript semantics

### 2. Integration with Backend Tests
Add to pytest:

```python
# waffen-tactics/tests/test_frontend_replay.py
def test_frontend_replay_matches_backend():
    """Run combat, save events, replay with Node.js, assert no desyncs"""
    events = run_combat_with_callbacks()
    save_to_json(events, 'temp_events.json')
    result = subprocess.run(['node', 'test-event-replay.mjs', 'temp_events.json'])
    assert result.returncode == 0, "Frontend replay detected desyncs"
```

### 3. Visual Diff Tool
Create an HTML viewer that shows:
- Event timeline
- State snapshots
- Diffs highlighted in red/green
- Ability to step through events

### 4. Automatic Event Capture
Modify `game_combat.py` to optionally save all event streams:

```python
if os.getenv('SAVE_COMBAT_EVENTS'):
    with open(f'logs/combat_{seed}.json', 'w') as f:
        json.dump(all_events, f)
```

## Troubleshooting

### "Module not found" errors

The inline implementation avoids this, but if you try to import TypeScript:

```bash
# Install tsx for TypeScript execution
npm install -D tsx

# Run with tsx
npx tsx test-event-replay.ts
```

### Events missing `game_state`

Only `state_snapshot` events have `game_state`. If none are present:
- Backend might not be emitting snapshots (check `CombatSimulator`)
- Event stream might be truncated
- Check that snapshots are emitted every 1 second in simulation

### All desyncs at first snapshot

Usually means `units_init` event has wrong data:
- Check that synergy buffs are applied in event
- Verify star scaling is correct
- Ensure `buffed_stats` matches backend calculations

## See Also

- [`src/hooks/combat/applyEvent.ts`](../waffen-tactics-web/src/hooks/combat/applyEvent.ts) - Production event handler
- [`src/hooks/combat/desync.ts`](../waffen-tactics-web/src/hooks/combat/desync.ts) - Desync detection
- [`backend/services/combat_event_reconstructor.py`](../waffen-tactics-web/backend/services/combat_event_reconstructor.py) - Python validator
- [`docs/DESYNC_IMPROVEMENTS.md`](./DESYNC_IMPROVEMENTS.md) - Desync mitigation strategies
