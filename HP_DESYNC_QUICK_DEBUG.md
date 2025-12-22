# Quick HP Desync Debugging

## Your Current Desync Pattern

UI HP is **lower** than server HP, meaning:
- Frontend is taking MORE damage than backend
- Or frontend is not receiving healing/shields
- Or damage is being applied twice

## Immediate Diagnosis (2 Commands)

### 1. Browser Console (during combat with desync)

```javascript
// Check if attack events have authoritative HP
const attacks = eventLogger.getEvents().filter(e =>
  e.type === 'unit_attack' || e.type === 'attack'
)

const missingHp = attacks.filter(e => {
  const evt = e.event
  return evt.target_hp === undefined &&
         evt.unit_hp === undefined &&
         evt.post_hp === undefined &&
         evt.new_hp === undefined
})

console.log(`Total attacks: ${attacks.length}`)
console.log(`Missing authoritative HP: ${missingHp.length}`)

if (missingHp.length > 0) {
  console.error('❌ FOUND THE PROBLEM: Attack events missing target_hp')
  console.log('First few:', missingHp.slice(0, 5).map(e => ({
    seq: e.seq,
    attacker: e.event.attacker_name,
    target: e.event.target_name,
    damage: e.event.damage
  })))
} else {
  console.log('✅ All attacks have authoritative HP')
  console.log('Problem is elsewhere - checking for duplicates...')

  // Check for duplicate attacks
  const seqs = attacks.map(e => e.seq)
  const dupes = seqs.filter((s, i) => seqs.indexOf(s) !== i)
  if (dupes.length > 0) {
    console.error(`❌ FOUND THE PROBLEM: Duplicate attack events at seq: ${dupes}`)
  }
}
```

### 2. Check Backend Events

If attack events are missing `target_hp`, the backend is not emitting it correctly.

```bash
cd waffen-tactics-web/backend

# Run a test combat and check attack events
python3 debug_desync.py --seed 42 2>&1 | grep -A 3 "unit_attack\|attack" | head -50
```

Look for `target_hp` field in the output.

## Most Likely Causes (Ranked)

### 1. Backend Not Emitting target_hp (90% likely)

**Symptom:** Frontend warns in console:
```
⚠️ unit_attack event 45 missing authoritative HP - using fallback calculation (may desync)
```

**Why this causes desync:**
- Frontend calculates: `new_hp = old_hp - damage`
- Backend uses: `new_hp = old_hp - (damage * defense_multiplier)`
- Defense formula differs → HP diverges

**Fix:** Ensure backend includes `target_hp` in ALL attack events

**Location to check:**
- `waffen-tactics/src/waffen_tactics/services/event_canonicalizer.py` (`emit_damage` function)
- `waffen-tactics/src/waffen_tactics/services/combat_attack_processor.py`

### 2. Race Condition / State Mutation (8% likely)

**Symptom:** No warnings in console, but HP still wrong

**Why this causes desync:**
- Frontend state is mutated instead of immutably updated
- Old state leaks into new state
- Effects applied to wrong reference

**Check:** Look for mutations in `applyEvent.ts`:
```typescript
// BAD - mutation:
unit.hp = newHp

// GOOD - immutable:
return { ...unit, hp: newHp }
```

### 3. Duplicate Events (2% likely)

**Symptom:** Same `seq` number appears twice in event log

**Why this causes desync:**
- Same damage applied twice
- HP drops by 2x expected amount

**Fix:** SSE buffer deduplication or backend event_id checking

## Resolution Steps

### If Missing target_hp:

1. Find the attack emitter in backend:
```bash
cd waffen-tactics
grep -rn "def emit_damage" src/
```

2. Check if it includes `target_hp`:
```python
def emit_damage(...):
    payload = {
        'damage': damage,
        'target_hp': target_hp,  # MUST be here
        ...
    }
```

3. If missing, add it:
```python
# Calculate HP after damage
target_hp = max(0, target.hp - damage_dealt)
target.hp = target_hp  # Update unit state

payload = {
    'target_hp': target_hp,  # Add authoritative HP
    ...
}
```

### If target_hp Present But Wrong:

1. Check defense calculation:
```python
# In combat_attack_processor.py
defense_multiplier = 100.0 / (100.0 + target.defense)
damage_after_defense = int(round(raw_damage * defense_multiplier))
```

2. Check shield absorption:
```python
shield_absorbed = min(damage_after_defense, target.shield)
hp_damage = damage_after_defense - shield_absorbed
target_hp = max(0, target.hp - hp_damage)
```

3. Ensure `target_hp` is HP **after** all calculations

### If Duplicate Events:

1. Add event deduplication in SSE buffer:
```typescript
// In useCombatSSEBuffer.ts
const seenEventIds = new Set()
if (event.event_id && seenEventIds.has(event.event_id)) {
  console.warn(`Skipping duplicate event: ${event.event_id}`)
  return
}
seenEventIds.add(event.event_id)
```

## Quick Test

Run this specific combat that shows desync:

```bash
# If you know the seed
cd waffen-tactics-web/backend
python3 debug_desync.py --seed <your_seed>

# Check event at the seq where desync occurs
python3 debug_desync.py --seed <your_seed> 2>&1 | grep "seq.*66\|seq.*64"
```

Compare with frontend:
```javascript
eventLogger.getEvents().filter(e => e.seq === 66 || e.seq === 64)
```

## Expected Output When Fixed

Backend debugger:
```
✅ No desyncs detected! All events replay correctly.
```

Frontend console:
```
✅ No missing authoritative HP warnings
✅ HP matches server at every snapshot
```

## Summary

**Most likely issue:** Backend emitting `unit_attack` events without `target_hp` field, forcing frontend to calculate damage locally with different formula.

**Quick check:** Look for `⚠️ missing authoritative HP` warnings in browser console.

**Fix location:** Backend attack event emitter (event_canonicalizer.py or combat_attack_processor.py)
