# Desync Debugging Guide

This guide explains how to debug desync issues between the backend combat simulator and frontend event replay using the comprehensive debugging tools.

## Problem Overview

The desync you're seeing shows **stun effects present in server state but missing in UI state**:

```json
{
  "unit_id": "8d6d21ac",
  "unit_name": "Puszmen12",
  "diff": {
    "effects": {
      "ui": [],
      "server": [
        {
          "type": "stun",
          "duration": 1.5
        }
      ]
    }
  }
}
```

This indicates either:
1. `unit_stunned` events are not being emitted by the backend
2. Events are emitted but not received by the frontend
3. Events are received but not applied correctly
4. Events arrive out of sequence

## Debugging Tools

### 1. Backend Debugger (`debug_desync.py`)

Located at: `waffen-tactics-web/backend/debug_desync.py`

This tool replays combat events through the `CombatEventReconstructor` to validate that events are sufficient to reconstruct state.

#### Usage

```bash
cd waffen-tactics-web/backend

# Debug a specific combat with seed
python debug_desync.py --seed 42

# Debug from saved events file
python debug_desync.py events_combat.json

# Analyze missing events
python debug_desync.py --seed 42 --analyze-missing

# Quiet mode (less verbose)
python debug_desync.py --seed 42 --quiet
```

#### What it does

1. **Simulates or loads combat** - Captures all events emitted by the combat simulator
2. **Replays events** - Feeds events through `CombatEventReconstructor` one by one
3. **Validates at snapshots** - Compares reconstructed state with server snapshots
4. **Reports desyncs** - Shows exact sequence number and field where desync occurs
5. **Analyzes missing events** - Identifies effects in snapshots that have no corresponding application event

#### Example Output

```
================================================================================
DESYNC DETECTED at seq=137 (event index 45)
================================================================================
Event type: mana_update
Error: Effects mismatch for player unit 8d6d21ac at seq 137 (seed 42):
       reconstructed=[], snapshot=[('stun', None, None, None, 'source123', 0.6)]

Recent events for unit 8d6d21ac:
  seq=135 type=attack data={"target_id":"8d6d21ac","damage":50,...}
  seq=136 type=skill_cast data={"caster_id":"opp_2","skill":"Stunning Blow",...}
  seq=137 type=mana_update data={"unit_id":"8d6d21ac","current_mana":0}

⚠️  Missing unit_stunned event for 8d6d21ac (effect_id=abc-123-def)
    Snapshot seq=140, timestamp=1.4
    Effect details: {"type":"stun","duration":1.5,"source":"opp_2"}
```

This tells you:
- **Desync occurred at seq=137** during a `mana_update` event
- **The unit should have a stun effect** but doesn't in reconstructed state
- **No `unit_stunned` event was emitted** for this stun application
- The stun came from a skill at seq=136

### 2. Frontend Event Logger (`eventLogger.ts`)

Located at: `waffen-tactics-web/src/hooks/combat/eventLogger.ts`

This tool captures all events received by the frontend from the SSE stream.

#### Usage in Browser Console

The event logger is automatically enabled in development mode and available globally:

```javascript
// Print summary of all events
eventLogger.printSummary()

// Get all events
eventLogger.getEvents()

// Get specific event type
eventLogger.getEventsByType('unit_stunned')

// Get events for a specific unit
eventLogger.getEventsForUnit('8d6d21ac')

// Analyze desync for a unit (requires server snapshot)
const serverSnapshot = /* from DesyncInspector or API */
eventLogger.analyzeDesyncForUnit('8d6d21ac', serverSnapshot)

// Download events as JSON file
eventLogger.downloadLog('combat_events.json')

// Export to JSON string
const json = eventLogger.exportToJSON()

// Clear logs
eventLogger.clear()
```

#### Example Analysis

```javascript
// When you see a desync in DesyncInspector, analyze it:
eventLogger.analyzeDesyncForUnit('8d6d21ac', {
  id: '8d6d21ac',
  effects: [
    { type: 'stun', id: 'abc-123', duration: 1.5 }
  ]
})
```

Output:
```
================================================================================
DESYNC ANALYSIS FOR UNIT: 8d6d21ac
================================================================================

Total events affecting this unit: 15

Events by type:
  unit_attack: 5
  mana_update: 8
  stat_buff: 2

Effect application events: 2
  seq=50 type=stat_buff effect_id=def-456
  seq=75 type=stat_buff effect_id=ghi-789

Server snapshot effects: 3
  type=stun id=abc-123 stat=undefined value=undefined
    ⚠️  NO MATCHING EVENT FOUND for effect_id=abc-123
  type=buff id=def-456 stat=attack value=20
    ✅ Found matching event at seq=50
  type=buff id=ghi-789 stat=defense value=15
    ✅ Found matching event at seq=75
```

This confirms that the `unit_stunned` event with `effect_id=abc-123` **was never received by the frontend**.

### 3. Combined Workflow

To fully diagnose a desync:

#### Step 1: Reproduce on Backend

```bash
cd waffen-tactics-web/backend

# Run with the seed that shows desync
python debug_desync.py --seed 42 --analyze-missing
```

This will tell you if the backend is **emitting** the necessary events.

**Possible outcomes:**

- ✅ **No desyncs detected** → Backend is emitting correctly, issue is in SSE transmission or frontend
- ❌ **Desync detected** → Backend is not emitting necessary events

#### Step 2: Check Frontend Reception

1. Trigger the combat in the web UI
2. Open browser console
3. Run:

```javascript
// Wait for combat to finish, then:
eventLogger.printSummary()

// Check if unit_stunned events were received
const stunEvents = eventLogger.getEventsByType('unit_stunned')
console.log(`Received ${stunEvents.length} stun events:`, stunEvents)

// Download for comparison with backend
eventLogger.downloadLog('frontend_events.json')
```

4. Compare `frontend_events.json` with backend event output

**Possible outcomes:**

- ✅ **Same event count** → Events are transmitted correctly, issue is in `applyEvent.ts`
- ❌ **Missing events** → SSE stream is dropping events

#### Step 3: Check Event Application

If events are received but desync still occurs, the issue is in `applyEvent.ts`.

1. Look at the `unit_stunned` handler in [applyEvent.ts:460-483](waffen-tactics-web/src/hooks/combat/applyEvent.ts#L460-L483)
2. Check console for `[EFFECT DEBUG]` logs during combat
3. Verify effect is being added to unit:

```javascript
// During combat, watch for:
// [EFFECT DEBUG] Applying stun to 8d6d21ac: {id: "abc-123", type: "stun", ...}
// [EFFECT DEBUG] 8d6d21ac effects before: 0, after: 1
```

If you see these logs but the effect is missing in the desync, there's a state mutation issue.

## Common Issues and Fixes

### Issue 1: Backend Not Emitting Events

**Symptom:** Backend debugger shows missing events
**Location:** Backend event emitters in `waffen-tactics/src/waffen_tactics/services/`

**Fix:**
1. Find where the effect is applied (e.g., in `skill_executor.py` or effect processors)
2. Ensure it calls the canonical emitter:

```python
from waffen_tactics.services.event_canonicalizer import emit_unit_stunned

# When applying stun
emit_unit_stunned(
    event_callback,
    target,
    duration=stun_duration,
    source=caster,
    side=get_side(target),
    timestamp=current_time
)
```

3. Verify `effect_id` is included in the emitted event

### Issue 2: Events Dropped in SSE Stream

**Symptom:** Backend emits events but frontend doesn't receive them
**Location:** `waffen-tactics-web/backend/routes/game_combat.py`

**Check:**
1. SSE mapping function includes the event type
2. Event is yielded correctly

```python
if event_type == 'unit_stunned':
    yield f"data: {json.dumps({
        'type': 'unit_stunned',
        'seq': event_data.get('seq'),
        'unit_id': event_data.get('unit_id'),
        'duration': event_data.get('duration'),
        'effect_id': event_data.get('effect_id'),  # CRITICAL
        ...
    })}\n\n"
```

### Issue 3: Frontend Not Applying Events

**Symptom:** Events received but not applied
**Location:** `waffen-tactics-web/src/hooks/combat/applyEvent.ts`

**Check:**
1. Handler exists for the event type (line 460 for `unit_stunned`)
2. Effect object is correctly constructed
3. Effect is added to unit's effects array
4. NEW effects array is created (no mutation):

```typescript
const newEffects = [...(u.effects || []), { ...effect }]  // GOOD
// NOT: u.effects.push(effect)  // BAD - mutation
```

### Issue 4: Effect Expiration Issues

**Symptom:** Effect is applied but expires too early/late

**Check:**
1. `expiresAt` calculation uses correct `simTime`:
```typescript
expiresAt: event.duration ? ctx.simTime + event.duration : undefined
```

2. Backend emits `effect_expired` events when effects expire
3. Frontend handles `effect_expired` by removing the effect

## Desync Pattern: Stun Effects Missing

Based on your specific desync, here's the targeted investigation:

### Check 1: Is Backend Emitting `unit_stunned`?

```bash
cd waffen-tactics-web/backend
python debug_desync.py --seed <your_seed> 2>&1 | grep unit_stunned
```

Expected output if working:
```
  Event 45: seq=136 type=unit_stunned unit=8d6d21ac
  Event 52: seq=143 type=unit_stunned unit=5801d77e
```

If empty, backend is **not emitting** stun events.

### Check 2: Where Are Stuns Applied?

Search for stun application in backend:

```bash
cd ../..
grep -r "emit_unit_stunned" waffen-tactics/src/waffen_tactics/services/
```

Common locations:
- `effects/stun.py` - Stun effect handler
- `skill_executor.py` - Skills that stun
- `combat_simulator.py` - Direct stun applications

### Check 3: Verify Effect ID Inclusion

The `unit_stunned` event MUST include `effect_id`:

```python
# In event_canonicalizer.py:607
payload = {
    'unit_id': getattr(target, 'id', None),
    'duration': duration,
    'effect_id': effect_id,  # CRITICAL - must be present
    ...
}
```

Frontend uses this to track effects.

## Quick Diagnosis Script

Run this in browser console after a desync:

```javascript
// Quick desync diagnosis
const desync = /* copy from DesyncInspector */;
const unitId = desync.unit_id;

console.log('=== DESYNC DIAGNOSIS ===');
console.log('Unit:', unitId);
console.log('Missing effects:', desync.diff.effects.server);

// Check if we received application events
const allEvents = eventLogger.getEventsForUnit(unitId);
console.log(`Total events for unit: ${allEvents.length}`);

const effectEvents = allEvents.filter(e =>
  ['unit_stunned', 'stat_buff', 'shield_applied', 'damage_over_time_applied'].includes(e.type)
);
console.log(`Effect application events: ${effectEvents.length}`, effectEvents);

// Check what we're missing
desync.diff.effects.server.forEach(serverEffect => {
  const found = effectEvents.some(e => {
    // Match by type and approximate timing
    return e.event.type === 'unit_stunned' && serverEffect.type === 'stun';
  });
  console.log(`Effect ${serverEffect.type}: ${found ? '✅ FOUND' : '❌ MISSING'}`);
});
```

## Advanced: Event Sequence Validation

To ensure events arrive in order:

```javascript
const events = eventLogger.getEvents();
const seqs = events.map(e => e.seq).filter(s => s >= 0);
for (let i = 1; i < seqs.length; i++) {
  if (seqs[i] < seqs[i-1]) {
    console.error(`❌ Out of order: seq ${seqs[i]} after ${seqs[i-1]}`);
  }
}
```

## Support

If you're still stuck after following this guide:

1. Capture backend events: `python debug_desync.py --seed <seed> > backend_log.txt`
2. Capture frontend events: `eventLogger.downloadLog('frontend_events.json')`
3. Export desync log from DesyncInspector
4. Compare the three to find the gap

The issue is likely one of:
- Event not emitted (check `backend_log.txt`)
- Event emitted but not transmitted (compare backend vs frontend event count)
- Event transmitted but not applied (check `applyEvent.ts` handler)
