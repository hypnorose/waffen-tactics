# Complete Desync Debugging Guide

## You Have Two Types of Desyncs

Based on your reports, you're experiencing:

1. **Effect Desyncs** - Stun effects missing in UI but present in server
2. **HP Desyncs** - HP values diverging (UI lower than server)

Both have different root causes and fixes.

---

## 🎯 Quick Start: Identify Your Desync Type

### In Browser Console After Combat:

```javascript
// Check for missing authoritative HP (HP desync)
const attacks = eventLogger.getEvents().filter(e =>
  e.type === 'unit_attack' || e.type === 'attack'
)
const missingHp = attacks.filter(e => {
  const evt = e.event
  return !evt.target_hp && !evt.unit_hp && !evt.post_hp && !evt.new_hp
})

if (missingHp.length > 0) {
  console.log('🔴 HP DESYNC: Attack events missing authoritative HP')
  console.log('   Fix: Backend must emit target_hp in attack events')
} else {
  console.log('✅ HP: All attacks have authoritative HP')
}

// Check for missing effect events (effect desync)
const stunEvents = eventLogger.getEventsByType('unit_stunned')
const statBuffEvents = eventLogger.getEventsByType('stat_buff')

console.log(`Effect events received:`)
console.log(`  unit_stunned: ${stunEvents.length}`)
console.log(`  stat_buff: ${statBuffEvents.length}`)

// If desync shows effects in server but counts are 0, effects aren't being emitted
```

---

## 🔴 HP Desync (UI HP < Server HP)

### Problem
Frontend calculates damage differently than backend, causing HP to diverge.

### Root Cause
Backend emits attack events **without** `target_hp` field, forcing frontend to calculate:
```typescript
// Frontend fallback (WRONG):
newHp = oldHp - damage  // Simple subtraction

// Backend actual (CORRECT):
newHp = oldHp - (damage * defenseMultiplier)  // Complex formula
```

### Quick Fix Check

**Browser Console:**
```javascript
const attacks = eventLogger.getEvents().filter(e => e.type === 'unit_attack')
console.log('Sample attack:', attacks[0]?.event)
// Should see: { target_hp: 450, damage: 50, ... }
// If target_hp is undefined → THAT'S THE PROBLEM
```

### Fix Location

**Backend:** `waffen-tactics/src/waffen_tactics/services/event_canonicalizer.py`

Find `emit_damage()` or attack event emission and ensure it includes:
```python
payload = {
    'damage': damage_dealt,
    'target_hp': target_hp,  # ← MUST BE HERE
    'shield_absorbed': shield_absorbed,
    'target_id': target.id,
    'seq': seq,
    'timestamp': timestamp
}
```

### Verification

After fix:
1. Run backend debugger: `python3 debug_desync.py --seed 42`
2. Should show: `✅ No desyncs detected!`
3. Frontend console: No `⚠️ missing authoritative HP` warnings

**Full Guide:** [HP_DESYNC_QUICK_DEBUG.md](HP_DESYNC_QUICK_DEBUG.md)

---

## 🔴 Effect Desync (Stun/Buff Missing in UI)

### Problem
Backend applies effects to unit state but doesn't emit corresponding events. Frontend never knows to add the effect.

### Root Cause
Code applies effect directly without calling canonical emitter:
```python
# WRONG:
target._stunned = True
target.effects.append({'type': 'stun', 'duration': 1.5})
# ^ Backend state has stun, but frontend never gets event!

# RIGHT:
emit_unit_stunned(event_callback, target, duration=1.5, ...)
# ^ Applies stun AND emits event
```

### Quick Check

**Browser Console:**
```javascript
// If desync shows missing stun:
const stunEvents = eventLogger.getEventsByType('unit_stunned')
console.log(`Stun events received: ${stunEvents.length}`)
// If 0 but desync shows stuns in server → events not emitted

// Check specific unit:
eventLogger.analyzeDesyncForUnit('unit_id', serverSnapshot)
```

**Backend:**
```bash
cd waffen-tactics-web/backend
python3 debug_desync.py --seed 42 --analyze-missing

# Will show:
# ⚠️ Missing unit_stunned event for unit_123 (effect_id=abc)
```

### Fix Location

**Backend:** Find where stuns are applied

```bash
cd waffen-tactics
# Find stun applications:
grep -rn "_stunned = True" src/
grep -rn "type.*stun" src/ | grep append
```

Replace with canonical emitter:
```python
from waffen_tactics.services.event_canonicalizer import emit_unit_stunned

# Instead of:
# target._stunned = True
# Do:
emit_unit_stunned(
    event_callback,
    target,
    duration=stun_duration,
    source=caster,
    side=get_side(target),
    timestamp=current_time
)
```

### Verification

After fix:
1. Backend debugger: `python3 debug_desync.py --seed 42 --analyze-missing`
2. Should show: `Effect events emitted: unit_stunned: 8` (non-zero)
3. Frontend: `eventLogger.getEventsByType('unit_stunned').length > 0`

**Full Guide:** [DESYNC_DEBUGGING_GUIDE.md](DESYNC_DEBUGGING_GUIDE.md)

---

## 🛠️ Debugging Tools Reference

### Backend Debugger

```bash
cd waffen-tactics-web/backend

# Basic test
python3 debug_desync.py --seed 42

# Analyze missing events
python3 debug_desync.py --seed 42 --analyze-missing

# Test saved events
python3 debug_desync.py combat_events.json

# Quiet mode (less verbose)
python3 debug_desync.py --seed 42 --quiet
```

**What it does:**
- Simulates combat with given seed
- Replays events through reconstructor
- Validates state matches snapshots
- Reports missing events

### Frontend Event Logger

```javascript
// In browser console (available as window.eventLogger):

// Summary of all events
eventLogger.printSummary()

// Get specific event types
eventLogger.getEventsByType('unit_stunned')
eventLogger.getEventsByType('unit_attack')

// Get events for unit
eventLogger.getEventsForUnit('unit_id')

// Analyze desync
eventLogger.analyzeDesyncForUnit('unit_id', serverSnapshot)

// Download events
eventLogger.downloadLog('events.json')

// Export JSON
const json = eventLogger.exportToJSON()

// Clear log
eventLogger.clear()
```

**What it does:**
- Captures all SSE events
- Counts by type
- Detects sequence gaps
- Compares with server snapshots

---

## 📋 Step-by-Step Debugging Workflow

### Step 1: Reproduce the Desync

1. Note which units show desync in DesyncInspector
2. Note the `seq` number where desync occurs
3. Note the field (hp, effects, etc.)

### Step 2: Backend Validation

```bash
cd waffen-tactics-web/backend

# If you know the seed:
python3 debug_desync.py --seed <seed> --analyze-missing

# Or use saved events:
python3 debug_desync.py events.json --analyze-missing
```

**Look for:**
- `❌ Desync detected at seq=X` → Backend has bug
- `⚠️ Missing <event_type> event for unit` → Event not emitted
- `✅ No desyncs` → Backend OK, issue is in transmission or frontend

### Step 3: Frontend Validation

```javascript
// Print summary
eventLogger.printSummary()

// For HP desyncs:
const attacks = eventLogger.getEvents().filter(e =>
  e.type === 'unit_attack' || e.type === 'attack'
)
console.log(`Total attacks: ${attacks.length}`)

// Check if missing target_hp:
const missingHp = attacks.filter(e => {
  const evt = e.event
  return !evt.target_hp && !evt.unit_hp && !evt.post_hp
})
console.log(`Missing HP: ${missingHp.length}`)

// For effect desyncs:
const effects = eventLogger.getEvents().filter(e =>
  ['unit_stunned', 'stat_buff', 'shield_applied', 'damage_over_time_applied'].includes(e.type)
)
console.log(`Effect events: ${effects.length}`)
```

**Compare counts:**
- Backend shows N events, frontend shows N events → Good
- Backend shows N events, frontend shows < N events → SSE dropping events
- Backend shows < N events needed by snapshots → Backend not emitting

### Step 4: Identify the Gap

| Backend | Frontend | Issue | Fix |
|---------|----------|-------|-----|
| ❌ Desync | N/A | Backend not emitting events | Add canonical emitters |
| ✅ No desync | Fewer events | SSE dropping events | Check SSE mapping |
| ✅ No desync | Same events | Frontend not applying | Check applyEvent.ts |

### Step 5: Fix and Verify

1. **Apply fix** based on issue identified
2. **Test backend:** `python3 debug_desync.py --seed 42`
3. **Test frontend:** Run combat, check console for warnings
4. **Verify:** No desyncs in DesyncInspector

---

## 📚 Documentation Index

- **[DESYNC_QUICK_REFERENCE.md](DESYNC_QUICK_REFERENCE.md)** - Quick command reference
- **[HP_DESYNC_QUICK_DEBUG.md](HP_DESYNC_QUICK_DEBUG.md)** - HP-specific debugging
- **[HP_DESYNC_ANALYSIS.md](HP_DESYNC_ANALYSIS.md)** - Detailed HP desync analysis
- **[DESYNC_DEBUGGING_GUIDE.md](DESYNC_DEBUGGING_GUIDE.md)** - Effect desync guide
- **[DESYNC_DEBUGGING_SUMMARY.md](DESYNC_DEBUGGING_SUMMARY.md)** - Tool overview

---

## 🎯 Your Specific Issues

### Issue 1: Stun Effects Missing (seq=1-3, timestamp=0.1)
**Type:** Effect desync
**Units:** Puszmen12, Miki, Frajdzia
**Diagnosis:** Backend likely not emitting `unit_stunned` events
**Fix:** Find stun application in skill effects, add `emit_unit_stunned()` call

### Issue 2: HP Divergence (seq=42-80, timestamp=0.7-1.1)
**Type:** HP desync
**Units:** Mrozu, RafcikD, Beudzik, maxas12
**Diagnosis:** Attack events probably missing `target_hp` field
**Fix:** Add `target_hp` to attack event payload in `emit_damage()`

---

## ✅ Success Criteria

After fixes:

**Backend:**
```bash
$ python3 debug_desync.py --seed 42
✅ No desyncs detected! All events replay correctly.
```

**Frontend:**
```javascript
eventLogger.printSummary()
// ✅ No gaps in sequence numbers
// ✅ No console warnings about missing HP
// DesyncInspector shows: No desyncs
```

---

## 🆘 Still Stuck?

1. Capture logs:
   - Backend: `python3 debug_desync.py --seed <seed> > backend.txt`
   - Frontend: `eventLogger.downloadLog('frontend.json')`
   - Desync: Copy JSON from DesyncInspector

2. Compare:
   - Event counts (backend vs frontend)
   - Specific events at desync `seq` number
   - Field presence (target_hp, effect_id, etc.)

3. The gap will be obvious:
   - Missing events → Backend emission
   - Different event count → SSE transmission
   - Same events, wrong result → Frontend application

Good luck! The tools will pinpoint exactly where the issue is. 🔍
