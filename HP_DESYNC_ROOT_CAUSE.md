# HP Desync Root Cause Analysis

## Problem Summary

UI shows **lower HP** than server snapshots consistently across all units.

**Pattern from user data:**
```
RafcikD: UI=1136, Server=1187 (diff: -51)
FalconBalkon: UI=533, Server=600 (diff: -67)
Mrozu: UI=567, Server=650 (diff: -83)
Capybara: UI=551, Server=630 (diff: -79)
Dumb: UI=647, Server=720 (diff: -73)
```

**Every case**: UI HP < Server HP

This means frontend is applying **MORE damage** than backend.

## Root Cause Found

### Backend (Correct) ✅

`emit_damage()` in event_canonicalizer.py:678-758:
```python
# Line 735-750:
payload = {
    'pre_hp': pre_hp,
    'post_hp': post_hp,
    'applied_damage': applied,
    'damage': applied,  # Same as applied_damage
    'target_hp': post_hp,  # ✅ Authoritative HP AFTER damage
    'new_hp': post_hp,
    'unit_hp': post_hp,
    'shield_absorbed': shield_absorbed,
    ...
}
```

**Key**: `damage` field = TOTAL applied damage (already includes shield absorption)

### Frontend (Buggy) ❌

`applyEvent.ts:97-143` handles `unit_attack` events:

```typescript
// Lines 100-111: Try to use authoritative HP
if (event.unit_hp !== undefined) {
    newHp = event.unit_hp  // ✅ Uses server HP if present
} else if (event.target_hp !== undefined) {
    newHp = event.target_hp  // ✅ Uses server HP if present
} 
// ... other authoritative HP fields ...

// Lines 126-142: FALLBACK (triggered when HP fields missing)
} else if (event.damage !== undefined) {
    console.warn(`⚠️ unit_attack event missing authoritative HP`)
    const damage = event.damage
    const hpDamage = damage - shieldAbsorbed  // ❌ BUG HERE!
    const calcHp = Math.max(0, oldHp - hpDamage)
    ...
}
```

### The Bug (Line 131)

```typescript
const hpDamage = damage - shieldAbsorbed  // ❌ WRONG!
```

**Problem**: `event.damage` already equals the applied damage AFTER shield absorption.

**Example scenario:**
- Unit has 100 HP, 20 shield
- Attack does 50 raw damage
- Shield absorbs 20, HP takes 30 damage

**Backend calculates:**
```python
applied = raw_damage - shield_absorbed = 50 - 20 = 30
payload = {
    'damage': 30,  # Applied damage to HP
    'shield_absorbed': 20
}
```

**Frontend fallback calculates:**
```typescript
hpDamage = damage - shieldAbsorbed = 30 - 20 = 10  // ❌ WRONG!
newHp = 100 - 10 = 90  // Should be 70!
```

**Result**: Frontend thinks unit has 90 HP, server knows it has 70 HP.

**Diff**: -20 (exactly the shield_absorbed amount!)

## Verification

Looking at user's HP differences:
- FalconBalkon: -67 diff
- Mrozu: -83 diff  
- Capybara: -79 diff
- Dumb: -73 diff

These are consistent with cumulative shield absorption errors over multiple attacks!

Each attack with shield absorption causes the frontend to apply LESS damage than backend, accumulating over time.

## When Does This Happen?

The fallback path (line 126) is triggered when:
1. Backend event missing ALL authoritative HP fields
2. OR frontend receiving events from older code version
3. OR SSE mapping not preserving HP fields

Check the SSE mapping in `game_combat.py`:

```python
def map_event_to_sse_payload(event_type, event_data):
    # Does this preserve target_hp/unit_hp fields?
```

## The Fix

### Option 1: Fix Frontend Fallback (Quick)

```typescript
// Line 131 in applyEvent.ts
const hpDamage = damage  // ✅ Don't subtract shield again!
```

**Reason**: `damage` already IS the HP damage (shield absorption already applied by backend)

### Option 2: Remove Fallback (Better)

```typescript
} else if (event.damage !== undefined) {
    console.error(`❌ unit_attack event ${event.seq} missing authoritative HP - cannot apply!`)
    // Don't apply damage - wait for next snapshot to sync
}
```

**Reason**: If backend isn't sending authoritative HP, we should fix backend, not guess.

### Option 3: Verify Backend Always Sends HP (Best)

Check that:
1. `emit_damage()` always includes `target_hp` ✅ (it does - line 748)
2. SSE mapping preserves these fields
3. No events bypass `emit_damage()`

## Testing the Fix

### Before Fix:
```javascript
// In browser console after combat:
eventLogger.getEventsByType('unit_attack').forEach(e => {
    console.log(`seq=${e.seq}: has unit_hp=${e.event.unit_hp !== undefined}, has target_hp=${e.event.target_hp !== undefined}`)
})
```

**Expect**: Most/all events should have `unit_hp` or `target_hp`

If they do, the frontend fallback should NEVER trigger (unless there's a bug).

### After Fix:
```javascript
// Check for desync warnings
// Should see: No HP desyncs OR warnings about missing HP in events
```

## Recommended Action

1. **First**: Check if events actually contain `target_hp`/`unit_hp`
2. **If yes**: Fix frontend fallback (Option 1)  
3. **If no**: Fix backend SSE mapping to preserve HP fields
4. **Finally**: Add validation to reject events without authoritative HP

## Summary

**Bug**: Frontend fallback double-subtracts shield absorption
**Location**: `applyEvent.ts:131`
**Fix**: Change `const hpDamage = damage - shieldAbsorbed` to `const hpDamage = damage`
**Verification**: Check browser console for "missing authoritative HP" warnings
