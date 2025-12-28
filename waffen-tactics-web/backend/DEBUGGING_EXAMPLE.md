# Desync Debugging Example

## Quick Start: Debug Your Desync

You reported desyncs with stun effects missing. Here's how to debug:

### Step 1: Run Backend Debugger

```bash
cd waffen-tactics-web/backend

# Test with a random seed to see if stuns work at all
python3 debug_desync.py --seed 42 --analyze-missing
```

This will:
1. Simulate a combat with seed 42
2. Replay all events through the reconstructor
3. Report any desyncs found
4. Analyze if effect events are missing

### Step 2: Look for Stun Events

```bash
# Capture output and search for stun events
python3 debug_desync.py --seed 42 2>&1 | grep -i stun
```

Expected output if stuns are working:
```
  Event 23: seq=45 type=unit_stunned unit=player_2
  Event 31: seq=53 type=unit_stunned unit=opp_1
```

If you see NO `unit_stunned` events, the backend is not emitting them!

### Step 3: Test Frontend Reception

1. Start your dev server:
```bash
cd waffen-tactics-web
npm run dev
```

2. Start backend:
```bash
cd backend
python3 api.py
```

3. Play a combat in the browser

4. Open browser console and run:
```javascript
// Print summary
eventLogger.printSummary()

// Check stun events
const stunEvents = eventLogger.getEventsByType('unit_stunned')
console.log('Stun events received:', stunEvents)

// Download for analysis
eventLogger.downloadLog('frontend_events.json')
```

5. Compare the count:
   - Backend: `grep -c unit_stunned backend_events.json`
   - Frontend: `grep -c unit_stunned frontend_events.json`

If counts don't match, events are being lost in SSE transmission.

## Example: Debugging Specific Unit

When you see a desync in the UI for unit `8d6d21ac`:

### Browser Console

```javascript
// Analyze the specific unit
eventLogger.analyzeDesyncForUnit('8d6d21ac', {
  id: '8d6d21ac',
  effects: [
    { type: 'stun', id: 'some-effect-id', duration: 1.5 }
  ]
})

// Get all events for this unit
const unitEvents = eventLogger.getEventsForUnit('8d6d21ac')
console.table(unitEvents.map(e => ({
  seq: e.seq,
  type: e.type,
  timestamp: e.timestamp
})))
```

### Backend

```bash
# Simulate the same combat
python3 debug_desync.py --seed <your_seed>

# Or analyze saved events
python3 debug_desync.py frontend_events.json
```

## Common Scenarios

### Scenario 1: Backend Not Emitting

**Symptom:** Backend debugger shows missing events

**Output:**
```
⚠️  Missing unit_stunned event for 8d6d21ac (effect_id=abc-123)
    Snapshot seq=140, timestamp=1.4
    Effect details: {"type":"stun","duration":1.5}
```

**Fix:** Check stun effect application in backend code:

```bash
# Find where stuns are applied
cd ../../waffen-tactics
grep -rn "emit_unit_stunned" src/waffen_tactics/services/

# Common locations:
# - src/waffen_tactics/services/effects/stun.py
# - src/waffen_tactics/services/skill_executor.py
```

Ensure the code calls `emit_unit_stunned` when applying stuns.

### Scenario 2: Events Lost in Transmission

**Symptom:**
- Backend: 10 `unit_stunned` events
- Frontend: 5 `unit_stunned` events

**Fix:** Check SSE mapping in `backend/routes/game_combat.py`:

```python
# Ensure unit_stunned is mapped
if event_type == 'unit_stunned':
    yield f"data: {json.dumps({
        'type': 'unit_stunned',
        'seq': event_data.get('seq'),
        'unit_id': event_data.get('unit_id'),
        'duration': event_data.get('duration'),
        'effect_id': event_data.get('effect_id'),
        # ... all other fields
    })}\n\n"
```

### Scenario 3: Events Received But Not Applied

**Symptom:**
- Frontend receives `unit_stunned` events
- Console shows: `[EFFECT EVENT] unit_stunned seq=137`
- But desync still occurs

**Fix:** Check `applyEvent.ts` handler:

```typescript
case 'unit_stunned':
  // Should create effect and add to unit
  const effect = {
    id: event.effect_id,
    type: 'stun',
    duration: event.duration,
    // ...
  }
  const newEffects = [...(u.effects || []), { ...effect }]
  return { ...u, effects: newEffects }
```

Verify:
1. Effect has correct structure
2. New array is created (no mutation)
3. Effect is added to correct unit (player vs opponent)

## Testing Workflow

### Test 1: Backend Consistency

```bash
# Run same seed multiple times
for i in {1..5}; do
  echo "=== Run $i ==="
  python3 debug_desync.py --seed 42 --quiet
done
```

All runs should have identical results (deterministic).

### Test 2: Event Count Validation

```bash
# Backend event count
python3 debug_desync.py --seed 42 2>&1 | grep "Effect events emitted:" -A 5
```

Expected:
```
Effect events emitted:
  unit_stunned: 8
  stat_buff: 15
  shield_applied: 6
  damage_over_time_applied: 4
```

Compare with frontend:
```javascript
eventLogger.printSummary()
// Should show same counts
```

### Test 3: Sequence Gap Detection

Frontend automatically checks for gaps:

```javascript
eventLogger.printSummary()
// Output will show:
// ✅ No gaps in sequence numbers
// OR
// ⚠️  Missing sequence numbers: 45, 46, 52
```

If gaps exist, events are being dropped.

## Automated Testing

You can create a test that runs backend validation:

```bash
cd waffen-tactics-web/backend

# Test multiple seeds
for seed in 1 2 3 5 10 42 100; do
  echo "Testing seed $seed..."
  python3 debug_desync.py --seed $seed --quiet || {
    echo "❌ Seed $seed FAILED"
    exit 1
  }
done

echo "✅ All seeds passed"
```

## What to Report

If you find a desync, capture:

1. **Backend log:**
```bash
python3 debug_desync.py --seed <seed> > backend_debug.txt 2>&1
```

2. **Frontend events:**
```javascript
eventLogger.downloadLog('frontend_events.json')
```

3. **Desync diff:**
From DesyncInspector, copy the JSON showing the mismatch

4. **Steps to reproduce:**
- Seed number (if using random combat)
- OR team compositions (if specific teams)

This will help identify whether the issue is:
- Backend emission
- SSE transmission
- Frontend application
- Event ordering
