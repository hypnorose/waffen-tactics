# Desync Debugging Tools - Summary

## Problem

Stun effects (and potentially other effects) appear in server snapshots but are missing in the frontend UI, causing desync errors.

## Solution: Comprehensive Debugging System

I've created a complete debugging system to identify where events are being lost:

### 🔧 Tools Created

#### 1. Backend Debugger (`waffen-tactics-web/backend/debug_desync.py`)

**Purpose:** Validates that backend emits correct events

**Usage:**
```bash
cd waffen-tactics-web/backend

# Test with specific seed
python3 debug_desync.py --seed 42

# Analyze missing events
python3 debug_desync.py --seed 42 --analyze-missing

# Test saved events
python3 debug_desync.py events.json
```

**What it does:**
- Simulates combat (or loads events from file)
- Replays events through `CombatEventReconstructor`
- Compares reconstructed state with server snapshots
- Reports exact sequence where desync occurs
- Identifies missing effect application events

**Example output:**
```
⚠️  Missing unit_stunned event for 8d6d21ac (effect_id=abc-123)
    Snapshot seq=140, timestamp=1.4
    Effect details: {"type":"stun","duration":1.5,"source":"opp_2"}
```

#### 2. Frontend Event Logger (`waffen-tactics-web/src/hooks/combat/eventLogger.ts`)

**Purpose:** Captures and analyzes events received by frontend

**Usage (in browser console):**
```javascript
// Print summary of received events
eventLogger.printSummary()

// Get specific event types
eventLogger.getEventsByType('unit_stunned')

// Analyze specific unit
eventLogger.analyzeDesyncForUnit('8d6d21ac', serverSnapshot)

// Download events for analysis
eventLogger.downloadLog('combat_events.json')

// Export to JSON
const json = eventLogger.exportToJSON()
```

**What it does:**
- Logs all events received from SSE stream
- Counts events by type
- Detects sequence gaps
- Compares received events with server snapshot
- Identifies missing effect application events

**Automatically enabled in development mode**

#### 3. Documentation

- **[DESYNC_DEBUGGING_GUIDE.md](DESYNC_DEBUGGING_GUIDE.md)** - Comprehensive guide with detailed explanations
- **[waffen-tactics-web/backend/DEBUGGING_EXAMPLE.md](waffen-tactics-web/backend/DEBUGGING_EXAMPLE.md)** - Quick start examples and common scenarios

## 🔍 How to Debug Your Desync

### Quick Diagnosis (3 steps)

#### Step 1: Check Backend Emission

```bash
cd waffen-tactics-web/backend
python3 debug_desync.py --seed 42 --analyze-missing
```

**Expected:** No desyncs, all `unit_stunned` events present
**If fails:** Backend is not emitting events correctly → Fix event emitters

#### Step 2: Check Frontend Reception

In browser console after combat:
```javascript
eventLogger.printSummary()
const stunEvents = eventLogger.getEventsByType('unit_stunned')
console.log('Received', stunEvents.length, 'stun events')
```

**Expected:** Same count as backend
**If different:** Events lost in SSE transmission → Fix SSE mapping

#### Step 3: Check Event Application

```javascript
// Analyze specific unit with desync
eventLogger.analyzeDesyncForUnit('8d6d21ac', {
  id: '8d6d21ac',
  effects: [{ type: 'stun', id: 'effect-id', duration: 1.5 }]
})
```

**Expected:** Events found for all effects
**If missing:** `applyEvent.ts` handler not applying correctly → Fix handler

## 🎯 For Your Specific Issue

Based on your desync showing missing stun effects:

### Immediate Investigation

1. **Run backend test:**
```bash
cd waffen-tactics-web/backend
python3 debug_desync.py --seed 42 2>&1 | grep -i "unit_stunned\|stun"
```

Look for:
- `unit_stunned` events being emitted
- Any "Missing unit_stunned event" warnings

2. **Check event emission in code:**
```bash
cd ../../waffen-tactics
grep -rn "emit_unit_stunned" src/waffen_tactics/services/
```

Verify stun effects call the canonical emitter.

3. **Test in browser:**
- Start combat
- Open console
- Run: `eventLogger.getEventsByType('unit_stunned')`
- Check if events were received

### Likely Causes

Based on the pattern (effects in server, missing in UI):

**Most Likely: Backend not emitting `unit_stunned` events**
- Skills apply stun directly to unit state
- But forget to call `emit_unit_stunned()`
- Server state has the stun (applied directly)
- Frontend doesn't (never received event)

**Less Likely: SSE dropping events**
- Would show different event counts between backend/frontend
- Would affect multiple event types, not just stuns

**Unlikely: Frontend not applying**
- Handler exists at `applyEvent.ts:460`
- Would show in console logs if events received

## 🛠️ How to Fix

### If Backend Not Emitting

Find where stuns are applied (likely in skill effects):

```python
# BEFORE (broken):
target._stunned = True
target.stunned_expires_at = time + duration
target.effects.append({'type': 'stun', 'duration': duration})

# AFTER (correct):
from waffen_tactics.services.event_canonicalizer import emit_unit_stunned

emit_unit_stunned(
    event_callback,
    target,
    duration=duration,
    source=caster,
    side=get_side(target),
    timestamp=time
)
# This function will both apply the stun AND emit the event
```

### If SSE Dropping Events

Check `waffen-tactics-web/backend/routes/game_combat.py`:

```python
# Ensure unit_stunned is in the mapping
if event_type == 'unit_stunned':
    yield f"data: {json.dumps({
        'type': 'unit_stunned',
        'seq': event_data.get('seq'),
        'unit_id': event_data.get('unit_id'),
        'duration': event_data.get('duration'),
        'effect_id': event_data.get('effect_id'),
        'caster_name': event_data.get('caster_name'),
        'timestamp': event_data.get('timestamp'),
    })}\n\n"
```

### If Frontend Not Applying

The handler looks correct, but verify:

```typescript
// In applyEvent.ts:460
case 'unit_stunned':
  if (event.unit_id) {
    const effect = {
      id: event.effect_id,  // Must be present
      type: 'stun',
      duration: event.duration,
      expiresAt: event.duration ? ctx.simTime + event.duration : undefined
    }
    // Create NEW array (no mutation)
    const newEffects = [...(u.effects || []), { ...effect }]
    return { ...u, effects: newEffects }
  }
```

## 📊 Testing

### Automated Test Suite

```bash
cd waffen-tactics-web/backend

# Test multiple seeds
for seed in 1 2 5 10 42 100 205; do
  echo "Testing seed $seed..."
  python3 debug_desync.py --seed $seed --quiet || {
    echo "❌ FAILED at seed $seed"
    break
  }
done
```

### Integration with Existing Tests

The backend debugger works with your existing test event files:

```bash
# Test with real combat events
python3 debug_desync.py events_seed205.json
python3 debug_desync.py combat_events.json
```

## 🚀 Next Steps

1. **Run the diagnosis** (Step 1-3 above)
2. **Identify the gap** (backend emission / SSE / frontend application)
3. **Fix the root cause** (add emitters / fix mapping / fix handler)
4. **Validate with tests** (run debug_desync.py on multiple seeds)

## 📝 Notes

- Event logger is automatically available in dev mode as `window.eventLogger`
- Backend debugger uses the same `CombatEventReconstructor` that validates in tests
- Both tools work with the existing desync detection in `DesyncInspector` component
- All debugging is non-invasive - can be used on production builds

## 🔗 References

- [Backend Reconstructor](waffen-tactics-web/backend/services/combat_event_reconstructor.py)
- [Frontend Event Handler](waffen-tactics-web/src/hooks/combat/applyEvent.ts)
- [Event Canonicalizer](waffen-tactics/src/waffen_tactics/services/event_canonicalizer.py)
- [SSE Route](waffen-tactics-web/backend/routes/game_combat.py)

---

**Happy debugging! 🐛🔧**
