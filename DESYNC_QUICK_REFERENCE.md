# Desync Debugging - Quick Reference Card

## 🚨 When You See a Desync

**Symptom:** DesyncInspector shows effects in server but missing in UI

```json
{
  "unit_id": "8d6d21ac",
  "diff": {
    "effects": {
      "ui": [],
      "server": [{"type": "stun", "duration": 1.5}]
    }
  }
}
```

## 🔍 Quick Diagnosis (Copy-Paste Commands)

### 1️⃣ Backend Check
```bash
cd waffen-tactics-web/backend
python3 debug_desync.py --seed 42 --analyze-missing
```
✅ No desyncs → Backend OK
❌ Desyncs found → Backend missing events

### 2️⃣ Frontend Check
```javascript
// In browser console after combat:
eventLogger.printSummary()
eventLogger.getEventsByType('unit_stunned')
```
✅ Same count as backend → Reception OK
❌ Different count → SSE dropping events

### 3️⃣ Unit Analysis
```javascript
// Replace with your unit ID and server snapshot:
eventLogger.analyzeDesyncForUnit('8d6d21ac', {
  id: '8d6d21ac',
  effects: [{ type: 'stun', id: 'effect-id', duration: 1.5 }]
})
```
✅ Events found → Application OK
❌ Events missing → Check applyEvent.ts

## 🛠️ Common Fixes

### Fix 1: Backend Not Emitting Events

**Location:** `waffen-tactics/src/waffen_tactics/services/`

**Find the problem:**
```bash
cd waffen-tactics
grep -rn "target._stunned = True" src/
```

**Fix:**
```python
# WRONG:
target._stunned = True
target.effects.append({'type': 'stun', 'duration': duration})

# RIGHT:
from waffen_tactics.services.event_canonicalizer import emit_unit_stunned
emit_unit_stunned(event_callback, target, duration=duration,
                  source=caster, side=side, timestamp=time)
```

### Fix 2: SSE Not Transmitting Events

**Location:** `waffen-tactics-web/backend/routes/game_combat.py`

**Check:**
```python
if event_type == 'unit_stunned':
    yield f"data: {json.dumps({
        'type': 'unit_stunned',
        'unit_id': event_data.get('unit_id'),
        'duration': event_data.get('duration'),
        'effect_id': event_data.get('effect_id'),  # MUST include
        'seq': event_data.get('seq'),
        'timestamp': event_data.get('timestamp'),
    })}\n\n"
```

### Fix 3: Frontend Not Applying Events

**Location:** `waffen-tactics-web/src/hooks/combat/applyEvent.ts:460`

**Check:**
```typescript
case 'unit_stunned':
  const effect = {
    id: event.effect_id,  // MUST use event.effect_id
    type: 'stun',
    duration: event.duration,
    expiresAt: ctx.simTime + event.duration
  }
  // MUST create new array (no mutation)
  const newEffects = [...(u.effects || []), { ...effect }]
  return { ...u, effects: newEffects }
```

## 📦 Tools Available

### Backend Tool
```bash
cd waffen-tactics-web/backend
python3 debug_desync.py --help
```

**Options:**
- `--seed N` - Test specific seed
- `--analyze-missing` - Find missing events
- `--quiet` - Less verbose output
- `events.json` - Test saved events

### Frontend Tool (Browser Console)
```javascript
// Global: window.eventLogger

// Commands:
eventLogger.printSummary()
eventLogger.getEvents()
eventLogger.getEventsByType('unit_stunned')
eventLogger.getEventsForUnit('unit_id')
eventLogger.analyzeDesyncForUnit('unit_id', snapshot)
eventLogger.downloadLog('events.json')
eventLogger.exportToJSON()
eventLogger.clear()
```

## 🧪 Testing

### Quick Test
```bash
cd waffen-tactics-web/backend
python3 debug_desync.py --seed 42
```

### Multiple Seeds
```bash
for seed in 1 2 5 10 42; do
  python3 debug_desync.py --seed $seed --quiet
done
```

### With Real Events
```bash
python3 debug_desync.py events_seed205.json
```

## 📋 Checklist for Bug Reports

When reporting a desync:

- [ ] Backend log: `python3 debug_desync.py --seed N > backend.txt`
- [ ] Frontend events: `eventLogger.downloadLog('frontend.json')`
- [ ] Desync JSON from DesyncInspector
- [ ] Seed number or team composition
- [ ] Steps to reproduce

## 📚 Full Documentation

- **Comprehensive Guide:** [DESYNC_DEBUGGING_GUIDE.md](DESYNC_DEBUGGING_GUIDE.md)
- **Examples:** [waffen-tactics-web/backend/DEBUGGING_EXAMPLE.md](waffen-tactics-web/backend/DEBUGGING_EXAMPLE.md)
- **Summary:** [DESYNC_DEBUGGING_SUMMARY.md](DESYNC_DEBUGGING_SUMMARY.md)

## 🎯 For Your Current Issue (Stun Effects)

### Immediate Action
```bash
# 1. Check if backend emits stun events
cd waffen-tactics-web/backend
python3 debug_desync.py --seed 42 2>&1 | grep unit_stunned

# 2. Find where stuns are applied
cd ../../waffen-tactics
grep -rn "emit_unit_stunned" src/waffen_tactics/services/

# 3. If no emitters found, search for direct stun application
grep -rn "_stunned = True" src/waffen_tactics/services/
```

### Expected Results
- Should see `emit_unit_stunned` calls in skill effects or stun handlers
- Each stun application should emit an event
- Backend debugger should show `unit_stunned` events in the log

### If Missing
Add canonical emitter where stuns are applied:
```python
emit_unit_stunned(callback, target, duration, source, side, timestamp)
```

---

**🔗 Quick Links:**
- Backend Debugger: `waffen-tactics-web/backend/debug_desync.py`
- Frontend Logger: `waffen-tactics-web/src/hooks/combat/eventLogger.ts`
- Event Handler: `waffen-tactics-web/src/hooks/combat/applyEvent.ts`
- Event Emitters: `waffen-tactics/src/waffen_tactics/services/event_canonicalizer.py`
