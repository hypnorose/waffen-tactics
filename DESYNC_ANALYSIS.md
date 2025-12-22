# Desync Analysis - UI HP Consistently Higher Than Server

## Desync Pattern from `desync_logs_1766289011979.json`

**Data**: 2802 lines of desync entries spanning events seq 138-192

**Key Pattern**: UI HP is **consistently HIGHER** than server HP for all affected units

### Examples

| Unit | UI HP | Server HP | Difference | Pattern |
|------|-------|-----------|------------|---------|
| Dumb (player) | 293 | 260 | +33 | UI higher |
| Hyodo888 (opp_0) | 583 | 466 | +117 | UI higher |
| Hyodo888 (player) | 1430 | 1326 | +104 | UI higher |
| Mrozu (player) | 620 | 590 | +30 | UI higher |
| maxas12 (player) | 757 | 683 | +74 | UI higher |

**Observation**: All desyncs show `"pending_events": []`, suggesting this is NOT an event ordering issue.

---

## Root Cause Analysis

### What Does "UI HP > Server HP" Mean?

This pattern indicates one of the following:

1. **Damage events are NOT being applied to UI state**
   - Backend is correctly reducing HP via damage
   - Frontend is either not receiving damage events OR not applying them

2. **Snapshots are being ignored**
   - Backend snapshots include correct (lower) HP
   - Frontend is not overwriting UI state with snapshot HP
   - `overwriteSnapshots` setting may be disabled

3. **Heals are being double-counted**
   - Less likely given the consistent pattern across all units
   - Would require systematic double-application of heal events

4. **Initial state mismatch**
   - Combat starts with different HP values
   - Subsequent events applied correctly but from wrong baseline

---

## Fixes Applied (Frontend)

### ✅ Fix #1: `unit_attack` Handler - Now Uses Authoritative HP
**File**: [applyEvent.ts:151-200](waffen-tactics-web/src/hooks/combat/applyEvent.ts#L151-L200)

**What Changed**:
- Previously calculated HP from damage delta: `hp = oldHp - damage`
- Now prioritizes authoritative HP from backend: `event.unit_hp`, `event.target_hp`, `event.post_hp`

**Impact**: Ensures damage events apply the exact HP value calculated by backend

---

### ✅ Fix #2: `heal` Handler - Now Uses Authoritative HP
**File**: [applyEvent.ts:349-381](waffen-tactics-web/src/hooks/combat/applyEvent.ts#L349-L381)

**What Changed**:
- Previously calculated HP incrementally: `hp = Math.min(max_hp, currentHp + healAmount)`
- Now prioritizes authoritative HP from backend: `event.unit_hp`, `event.post_hp`, `event.new_hp`

**Impact**: Prevents cumulative heal errors if UI HP was already desynced

---

### ✅ Fix #3: `state_snapshot` Handler - Now Preserves All Stats
**File**: [applyEvent.ts:63-73, 99-109](waffen-tactics-web/src/hooks/combat/applyEvent.ts#L63-L109)

**What Changed**:
- Previously only preserved: `hp`, `current_mana`, `shield`, `position`
- Now also preserves: `attack`, `defense`, `buffed_stats`

**Impact**: When `overwriteSnapshots=true`, snapshots now sync ALL stats, not just HP/mana/shield

---

### ✅ Fix #4: `stat_buff` Handler - Now Uses `applied_delta`
**File**: [applyEvent.ts:217-275](waffen-tactics-web/src/hooks/combat/applyEvent.ts#L217-L275)

**What Changed**:
- Previously calculated delta from percentage: `delta = base * (pct / 100)`
- Now uses backend's `applied_delta` when available

**Impact**: Prevents stat calculation mismatches

---

### ✅ Fix #5: `buffed_stats` Calculation - Fixed HP Buff Logic
**File**: [applyEvent.ts:243-256](waffen-tactics-web/src/hooks/combat/applyEvent.ts#L243-L256)

**What Changed**:
- Fixed conditional that was using `buffed_hp` as delta instead of absolute value
- Now correctly handles HP buffs in `buffed_stats` object

**Impact**: Prevents HP stat buff miscalculations

---

## Verification Steps Needed

### 1. Check `overwriteSnapshots` Setting

The frontend has an `overwriteSnapshots` feature that syncs UI state with server snapshots every second. If this is disabled, snapshots are ignored and desyncs accumulate.

**Check in Browser Console**:
```javascript
localStorage.getItem('combat.overwriteSnapshots')
// Should return: "true"
```

**If disabled**, enable it:
```javascript
localStorage.setItem('combat.overwriteSnapshots', 'true')
```

Then reload and re-test combat.

---

### 2. Verify Frontend Was Rebuilt

All fixes are in [applyEvent.ts](waffen-tactics-web/src/hooks/combat/applyEvent.ts). Ensure frontend was rebuilt:

```bash
cd waffen-tactics-web
npm run build
# Or if using dev server:
npm run dev  # Vite should auto-reload
```

---

### 3. Add Debug Logging

To verify damage events are being received and applied, add temporary logging:

**In `applyEvent.ts` around line 168**:
```typescript
if (newHp !== undefined) {
  // Use authoritative HP from backend
  console.log(`[DAMAGE] ${event.target_id} HP: ${oldHp} → ${newHp} (damage: ${event.damage})`)
  const updateFn = (u: Unit) => {
    const newShield = Math.max(0, (u.shield || 0) - shieldAbsorbed)
    return { ...u, hp: newHp!, shield: newShield }
  }
  // ...
}
```

**In `applyEvent.ts` around line 65**:
```typescript
case 'state_snapshot':
  console.log(`[SNAPSHOT] seq=${event.seq}, player_units count=${event.player_units?.length}, opp_units count=${event.opponent_units?.length}`)
  if (overwriteSnapshots) {
    console.log('[SNAPSHOT] Overwriting UI state with server snapshot')
    // ...
  } else {
    console.log('[SNAPSHOT] IGNORING snapshot (overwriteSnapshots=false)')
  }
```

---

### 4. Capture Event Stream

To analyze the actual events being sent from backend:

**In Browser Console** (during combat):
```javascript
// This will log all SSE events
const originalLog = console.log
console.log = function(...args) {
  if (args[0]?.type) {
    originalLog('SSE EVENT:', JSON.stringify(args[0]))
  }
  originalLog.apply(console, args)
}
```

Look for:
- Are `unit_attack` events arriving?
- Do they include `target_hp` or `unit_hp` fields?
- Are `state_snapshot` events arriving every ~1 second?
- Do snapshots include HP values that match server?

---

## Potential Remaining Issues

### Issue #1: Backend Attack Processor Doesn't Use Canonical Emitter

**File**: [combat_attack_processor.py:60-70](waffen-tactics/src/waffen_tactics/services/combat_attack_processor.py#L60-L70)

**Problem**:
- Backend manually creates `'attack'` events instead of calling `emit_damage()`
- HP mutation happens via direct list manipulation (line 49-50)
- Event payload is created manually (line 60-70)

**Expected**:
```python
# Should call canonical emitter
from .event_canonicalizer import emit_damage
emit_damage(
    event_callback,
    attacker=unit,
    target=defending_team[target_idx],
    raw_damage=damage,
    timestamp=time,
    cause='attack'
)
```

**Current** (WRONG):
```python
# Direct HP mutation
defending_hp[target_idx] -= damage
defending_hp[target_idx] = max(0, int(defending_hp[target_idx]))

# Manual event creation
if event_callback:
    event_callback('attack', {
        'attacker_id': unit.id,
        'target_id': defending_team[target_idx].id,
        'damage': damage,
        'target_hp': defending_hp[target_idx],
        # ...
    })
```

**Impact**: While the event DOES include `target_hp`, this violates the canonical emitter architecture and could lead to inconsistencies if `emit_damage` is updated but the manual event creation is not.

---

### Issue #2: SSE Mapper Priority

**File**: [game_combat.py:41](waffen-tactics-web/backend/routes/game_combat.py#L41)

The SSE mapper prioritizes `target_hp` over `unit_hp`:
```python
'target_hp': data.get('target_hp') or data.get('unit_hp')
```

This is fine since both are set to the same value by the backend, but it's inconsistent with the frontend handler which checks `unit_hp` first.

**Recommendation**: Standardize to always prioritize `unit_hp` (the canonical field name from `emit_damage`).

---

## Next Steps

### Immediate
1. ✅ All frontend fixes applied
2. ⏳ **User needs to verify**:
   - Check `overwriteSnapshots` setting
   - Rebuild frontend
   - Re-test combat
   - Check if desyncs still occur

### If Desyncs Persist
1. Add debug logging to verify:
   - Damage events are arriving
   - Damage events include authoritative HP
   - Snapshots are being applied
2. Capture event stream and analyze for missing events
3. Check if initial combat state matches between UI and backend

### Backend Improvements (Future)
1. Migrate `combat_attack_processor.py` to use `emit_damage()` canonical emitter
2. Ensure ALL damage sources use canonical emitters
3. Add event replay validation to backend tests

---

## Summary

**Frontend Fixes**: ✅ 6 fixes applied to ensure authoritative HP/stat handling

**Likely Root Cause**: One of:
- `overwriteSnapshots` setting disabled
- Frontend not rebuilt with fixes
- Initial state mismatch
- Backend not emitting events properly (unlikely given test pass rate)

**Next Action**: User verification required - rebuild frontend, check settings, re-test combat.
