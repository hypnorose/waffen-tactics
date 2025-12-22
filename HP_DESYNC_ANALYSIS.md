# HP Desync Analysis

## Pattern Detected

Multiple units showing UI HP **lower** than server HP:

```
Mrozu:    UI=452, Server=578  (diff=-126)
Mrozu:    UI=578, Server=650  (diff=-72)
RafcikD:  UI=972, Server=1028 (diff=-56)
RafcikD:  UI=1028, Server=1148 (diff=-120)
RafcikD:  UI=1148, Server=1248 (diff=-100)
Beudzik:  UI=501, Server=533  (diff=-32)
Beudzik:  UI=533, Server=600  (diff=-67)
maxas12:  UI=720, Server=800  (diff=-80)
```

## Key Observations

1. **UI HP is consistently LOWER than server HP**
   - This means frontend is applying MORE damage than backend
   - Or frontend is applying damage when backend isn't

2. **Desyncs occur during `unit_attack` events**
   - Suggests damage calculation divergence
   - Could be shield absorption issues
   - Could be defense calculation issues

3. **Differences vary widely** (32-126 HP)
   - Not a fixed offset
   - Proportional to unit's stats or attack damage

4. **All occur around timestamp 0.7-1.1s**
   - Early combat phase
   - Possibly related to initial attacks or skill casts

## Likely Causes

### 1. Defense Calculation Mismatch

**Backend:** Uses complex defense formula with diminishing returns
**Frontend:** Might be calculating damage differently

```python
# Backend (combat_attack_processor.py)
def calculate_defense_multiplier(defense):
    return 100.0 / (100.0 + defense)

damage_dealt = int(round(raw_damage * defense_multiplier))
```

**Frontend should use AUTHORITATIVE HP from events**, not calculate it!

### 2. Frontend Calculating Damage Locally

**Problem:** If frontend is calculating `new_hp = old_hp - damage` instead of using `event.target_hp`

```typescript
// WRONG:
u.hp = u.hp - event.damage  // Calculates locally

// RIGHT:
u.hp = event.target_hp  // Uses authoritative value from backend
```

### 3. Shield Absorption Timing

**Problem:** Frontend might be applying shield absorption incorrectly:
- Not subtracting `shield_absorbed` from shield
- Applying shield absorption to HP as well
- Shield expires between backend calculation and frontend application

### 4. Double Damage Application

**Problem:** Same attack event processed twice due to:
- Event replay bug
- Race condition
- Duplicate events in stream

## Debugging Steps

### Step 1: Check Event Emission

```bash
cd waffen-tactics-web/backend
python3 debug_desync.py --seed <seed_with_desync> > backend_log.txt 2>&1

# Look for attacks on the desynced units
grep -A 5 "target.*Mrozu" backend_log.txt | head -50
grep -A 5 "target.*RafcikD" backend_log.txt | head -50
```

Check if `target_hp` is included in attack events.

### Step 2: Frontend Event Inspection

In browser console:
```javascript
// Get all attacks on a specific unit
const attacks = eventLogger.getEventsForUnit('0fdb2620')  // Mrozu's ID
  .filter(e => e.type === 'unit_attack' || e.type === 'attack')

console.table(attacks.map(e => ({
  seq: e.seq,
  type: e.type,
  damage: e.event.damage,
  target_hp: e.event.target_hp,
  shield_absorbed: e.event.shield_absorbed
})))
```

Check if:
- `target_hp` is present in events
- Values match what backend logged
- Any duplicate events

### Step 3: Check applyEvent.ts Handler

Look at the attack/unit_attack handler in [applyEvent.ts](waffen-tactics-web/src/hooks/combat/applyEvent.ts):

```typescript
case 'unit_attack':
  if (event.target_id) {
    // Should use AUTHORITATIVE HP from event
    const authoritativeHp = event.unit_hp ?? event.target_hp ?? event.post_hp ?? event.new_hp

    if (authoritativeHp !== undefined) {
      // Set HP directly from event (CORRECT)
      unit.hp = authoritativeHp
    } else {
      // Calculate locally (WRONG - causes desync!)
      unit.hp = unit.hp - event.damage
    }
  }
```

## Quick Diagnosis Script

Run this to compare attack events:

```javascript
// In browser console after combat with desync
const desyncedUnitId = '0fdb2620'  // Mrozu
const attacks = eventLogger.getEventsForUnit(desyncedUnitId)
  .filter(e => e.type === 'unit_attack' || e.type === 'attack')

console.log('=== ATTACK EVENTS FOR DESYNCED UNIT ===')
attacks.forEach((e, i) => {
  const evt = e.event
  console.log(`Attack ${i+1}: seq=${e.seq}`)
  console.log(`  damage=${evt.damage}`)
  console.log(`  target_hp=${evt.target_hp} (authoritative)`)
  console.log(`  shield_absorbed=${evt.shield_absorbed}`)
  console.log(`  Expected HP after: ${evt.target_hp}`)
})

// Check if target_hp is missing
const missingHp = attacks.filter(e =>
  e.event.target_hp === undefined &&
  e.event.unit_hp === undefined &&
  e.event.post_hp === undefined
)

if (missingHp.length > 0) {
  console.error(`❌ ${missingHp.length} attacks missing authoritative HP!`)
  console.log('These events force frontend to calculate locally, causing desync:')
  console.table(missingHp.map(e => ({
    seq: e.seq,
    damage: e.event.damage,
    attacker: e.event.attacker_name
  })))
}
```

## Expected Fixes

### Fix 1: Ensure Backend Includes target_hp

In `combat_attack_processor.py` or event emitter:

```python
# Attack event MUST include authoritative HP
payload = {
    'attacker_id': attacker.id,
    'target_id': target.id,
    'damage': damage_dealt,
    'shield_absorbed': shield_absorbed,
    'target_hp': target_hp,  # CRITICAL - authoritative HP after damage
    'seq': seq,
    'timestamp': timestamp
}
```

### Fix 2: Frontend Uses Authoritative HP ONLY

In `applyEvent.ts`:

```typescript
case 'unit_attack':
case 'attack':
  if (event.target_id) {
    // Priority order for authoritative HP
    const authoritativeHp = event.target_hp ?? event.unit_hp ?? event.post_hp ?? event.new_hp

    if (authoritativeHp === undefined) {
      console.error(`❌ Attack event seq=${event.seq} missing authoritative HP!`)
      // TEMPORARILY calculate, but log error
      // This should be fixed by adding target_hp to backend event
    }

    const updateFn = (u: Unit) => ({
      ...u,
      hp: authoritativeHp ?? Math.max(0, u.hp - (event.damage || 0)),
      shield: Math.max(0, (u.shield || 0) - (event.shield_absorbed || 0))
    })

    // Apply to correct side
    if (event.target_id.startsWith('opp_')) {
      newState.opponentUnits = updateUnitById(newState.opponentUnits, event.target_id, updateFn)
    } else {
      newState.playerUnits = updateUnitById(newState.playerUnits, event.target_id, updateFn)
    }
  }
  break
```

### Fix 3: Add Validation

Add HP validation to detect when local calculation would diverge:

```typescript
// In applyEvent.ts, after applying damage
if (authoritativeHp !== undefined) {
  const calculatedHp = Math.max(0, oldHp - event.damage + (event.shield_absorbed || 0))
  if (Math.abs(calculatedHp - authoritativeHp) > 1) {
    console.warn(`HP calculation mismatch for ${event.target_id}:`,
      `calculated=${calculatedHp}, authoritative=${authoritativeHp}`,
      `diff=${authoritativeHp - calculatedHp}`)
  }
}
```

## Test Plan

1. **Add HP logging to backend**
   ```python
   print(f"[ATTACK] {attacker.name} -> {target.name}: dmg={damage} shield_abs={shield_absorbed} hp_before={hp_before} hp_after={target_hp}")
   ```

2. **Add HP logging to frontend**
   ```typescript
   console.log(`[ATTACK] ${event.attacker_name} -> ${event.target_name}: dmg=${event.damage} target_hp=${event.target_hp} old_hp=${oldHp}`)
   ```

3. **Run combat and compare logs**
   - Backend should show correct defense calculations
   - Frontend should show matching HP values
   - Any divergence shows where calculation differs

## Priority Actions

1. **Check if backend emits `target_hp`** in attack events
2. **Check if frontend uses `target_hp`** instead of calculating
3. **Add logging** to both sides for the same combat
4. **Compare logs** to find first divergence point

This is likely a simpler fix than the effect desync - just need to ensure authoritative HP transmission!
