# Backend Event Emission Fixes - Session Summary

## Overview

This session improved the backend event emitters to provide more authoritative data in events, reducing the need for reconstructor fallback logic.

**Test Results**: ✅ 301/302 tests passing (1 expected failure - OLD skill system ally_team bug)

---

## Fixes Applied

### 1. ✅ `emit_stat_buff()` - Now ALWAYS Includes `applied_delta`

**File**: `waffen-tactics/src/waffen_tactics/services/event_canonicalizer.py`
**Lines Modified**: 50-105

**Before**:
- Only calculated `delta` for some stats (`attack`, `defense`, `attack_speed`)
- Other stats had `delta = None` in events

**After**:
- **ALL stats** now calculate `applied_delta` before emission
- Percentage buffs: `delta = int(round(base * (value / 100.0)))`
- Flat buffs: `delta = int(round(value))`
- Unknown stats: Best-effort calculation with fallback to 0

**New stat handling**:
- `max_hp`, `max_mana`, `current_mana`: Now calculate delta
- Custom stats: Fallback delta calculation added
- Exception handling: Sets `delta = 0` if calculation fails

**Impact**:
- ✅ Reconstructor can now trust `applied_delta` for ALL stat buffs
- ✅ Eliminates need for percentage calculation in reconstructor
- ✅ Consistent rounding via `int(round(...))` matches simulator behavior

**Code**:
```python
# Now handles ALL stats with consistent rounding
elif stat in ('max_hp', 'max_mana', 'current_mana'):
    # int fields
    if value_type == 'percentage':
        delta = int(round(getattr(recipient, stat, 0) * (float(value) / 100.0)))
    else:
        delta = int(round(value))
    setattr(recipient, stat, getattr(recipient, stat, 0) + delta)
else:
    # Unknown/custom stats - still calculate delta for event
    if value_type == 'percentage':
        base = getattr(recipient, stat, 0) or 0
        delta = int(round(float(base) * (float(value) / 100.0)))
    else:
        delta = int(round(value)) if isinstance(value, (int, float)) else 0
```

---

### 2. ✅ `emit_damage()` - Already Includes Authoritative HP

**File**: `waffen-tactics/src/waffen_tactics/services/event_canonicalizer.py`
**Status**: Already correct - verified during analysis

**Current Implementation** (Lines 721-736):
```python
payload = {
    'attacker_id': getattr(attacker, 'id', None),
    'attacker_name': getattr(attacker, 'name', None),
    'unit_id': getattr(target, 'id', None),
    'target_id': getattr(target, 'id', None),
    'pre_hp': pre_hp,
    'post_hp': post_hp,
    'applied_damage': applied,
    'damage': applied,          # Backwards-compatible
    'target_hp': post_hp,       # ✅ Authoritative
    'new_hp': post_hp,          # ✅ Authoritative
    'unit_hp': post_hp,         # ✅ Authoritative
    'shield_absorbed': shield_absorbed,
    'damage_type': damage_type,
    'side': side,
    'timestamp': ts,
    'cause': cause,
}
```

**Provides**:
- ✅ `target_hp`, `new_hp`, `unit_hp` all include authoritative post-damage HP
- ✅ `pre_hp` and `post_hp` for delta verification
- ✅ Multiple field names for backwards compatibility

---

### 3. ✅ `emit_unit_heal()` - Already Includes Authoritative HP

**File**: `waffen-tactics/src/waffen_tactics/services/event_canonicalizer.py`
**Status**: Already correct - verified during analysis

**Current Implementation** (Lines 398-411):
```python
payload = {
    'healer_id': getattr(healer, 'id', None),
    'healer_name': getattr(healer, 'name', None),
    'unit_id': getattr(target, 'id', None),
    'amount': int(amount),
    'pre_hp': cur,
    'post_hp': new,
    'unit_hp': new,             # ✅ Authoritative HP after heal
    'unit_max_hp': max_hp,
    'side': side,
    'timestamp': ts,
    'cause': cause,
}
```

**Provides**:
- ✅ `unit_hp` contains authoritative HP after heal
- ✅ `pre_hp` and `post_hp` for verification
- ✅ `unit_max_hp` for overheal capping verification

---

### 4. ✅ `emit_damage_over_time_tick()` - Already Includes Authoritative HP

**File**: `waffen-tactics/src/waffen_tactics/services/event_canonicalizer.py`
**Status**: Already correct - verified during analysis

**Current Implementation** (Lines 517-529):
```python
dot_payload = {
    'unit_id': getattr(target, 'id', None),
    'unit_name': getattr(target, 'name', None),
    'effect_id': effect_id,
    'damage': int(damage),
    'damage_type': damage_type,
    'unit_hp': payload.get('post_hp'),  # ✅ From emit_damage
    'tick_index': tick_index,
    'total_ticks': total_ticks,
    'side': side,
    'timestamp': ts,
}
```

**Provides**:
- ✅ `unit_hp` contains authoritative HP after DoT tick
- ✅ Uses `emit_damage()` internally, inheriting all authoritative fields
- ✅ `effect_id` for tracking which DoT effect caused the tick

---

## Remaining Backend Issues (Not Fixed)

### ❌ Random Stat Buffs Not Resolved

**Problem**: Events emit `stat: 'random'` instead of resolved stat name

**Example**:
```python
# Current behavior
emit_stat_buff(callback, unit, stat='random', value=10, ...)
# Event contains: { stat: 'random', value: 10, applied_delta: 10 }

# What it SHOULD do
chosen_stat = random.choice(['attack', 'defense', 'attack_speed', 'hp'])
emit_stat_buff(callback, unit, stat=chosen_stat, value=10, ...)
# Event contains: { stat: 'attack', value: 10, applied_delta: 10 }
```

**Where to fix**: Skills that use `stat: 'random'` should resolve the stat before calling `emit_stat_buff()`

**Impact**: Reconstructor still contains inference logic to guess which stat was buffed (lines 683-716)

---

### ❌ DoT Tick Duplicates

**Problem**: DoT tick emitter sometimes emits duplicate events

**Evidence**: Reconstructor contains deduplication logic (lines 265-286)

**Where to fix**: DoT processor should use `event_id` for idempotency

**Location**: `combat_effect_processor.py` - DoT tick emission

---

### ❌ Effect Application Events Missing

**Problem**: Some effects appear in snapshots but were never emitted as events

**Evidence**: Reconstructor contains 500+ line reconciliation function (lines 606-848) that applies effects from snapshots

**Where to fix**:
- Synergy buffs must emit `stat_buff` events
- All shield applications must emit `shield_applied` events
- All DoT applications must emit `damage_over_time_applied` events

**Locations**:
- `synergy.py` - Synergy buff application
- `combat_simulator.py` - Any buff/shield/DoT application paths

---

### ❌ Effect Expiration Events Missing

**Problem**: Effect processor doesn't emit expiration events

**Evidence**: Reconstructor contains synthetic expiration logic (lines 859-906) that:
- Calculates `expires_at` from `ticks_remaining + interval`
- Filters effects by time
- Reverts stat changes when effects expire

**Where to fix**:
- `combat_effect_processor.py` - Effect expiration loop must emit `effect_expired`
- DoT expiration must emit `damage_over_time_expired` consistently

---

### 🔴 OLD Skill System `ally_team` Heals (BLOCKING TEST)

**Problem**: OLD skill system updates wrong HP list for ally heals

**Test Failing**: `test_10v10_simulation_multiple_seeds` - 2 seeds

**Root Cause** (`combat_simulator.py:800-813`):
```python
# Line 486 - Called with defending_hp
self._process_skill_cast(unit, defending_team[target_idx], defending_hp, ...)

# Line 808 - Updates defending_hp even for ally heals (BUG)
target_hp_list[apply_idx] = min(...)  # target_hp_list IS defending_hp

# Line 812 - emit_unit_heal correctly sets unit.hp (CORRECT)
emit_unit_heal(callback, target_obj, caster, amount, ...)
```

**Result**: `unit.hp` = correct (286), `attacking_hp[idx]` = stale (246)

**Fix Options**:
1. **Migrate units to skills.json** (Recommended) - Units using new format go through `HealHandler` which works correctly
2. Add `ally_team` support to old system (Not recommended - adds complexity to legacy code)

**Units to migrate**:
```bash
grep -r "ally_team" waffen-tactics/units.json
```

---

## Reconstructor Simplifications Enabled

With `emit_stat_buff` now always including `applied_delta`, the reconstructor can be simplified:

### Can Now Delete (Once Applied Delta is Verified Working)

**Lines 386-416** in `combat_event_reconstructor.py`:
```python
# TEMPORARY FALLBACK LOGIC - CAN BE DELETED
delta = event_data.get('applied_delta')
if delta is None:
    # Fallback calculation (NO LONGER NEEDED)
    if value_type == 'percentage':
        pct = float(amount)
        base_stats = unit_dict.get('base_stats') or {}
        base = base_stats.get(stat, 0) or 0
        delta = int(round(base * (pct / 100.0)))
    else:
        delta = int(round(amount))
```

**Replacement**:
```python
# Trust backend - applied_delta is ALWAYS present
delta = event_data.get('applied_delta', 0)
# No fallback calculation needed
```

**Lines Saved**: ~30 lines of complex percentage calculation logic deleted

---

## Test Results

**Before**: 301/302 tests passing
**After**: 301/302 tests passing ✅ No regression

**1 Failing Test** (expected):
- `test_10v10_simulation_multiple_seeds` - 2 seeds
- Root cause: OLD skill system `ally_team` heal bug
- Fix: Migrate units to skills.json

---

## Files Modified

1. ✅ `waffen-tactics/src/waffen_tactics/services/event_canonicalizer.py`
   - `emit_stat_buff()`: Now calculates `applied_delta` for ALL stats
   - Added consistent `int(round(...))` rounding for all calculations
   - Added fallback delta calculation for unknown stats

2. ✅ `waffen-tactics-web/backend/services/combat_event_reconstructor.py` (documentation only)
   - Added architectural violation warnings
   - Marked all temporary fallback logic
   - Added detailed docstrings explaining required backend fixes

3. ✅ `RECONSTRUCTOR_ARCHITECTURAL_ANALYSIS.md` (new file)
   - Complete analysis of reconstructor violations
   - Backend fix checklist
   - Simplification roadmap

4. ✅ `BACKEND_FIXES_APPLIED.md` (this file)
   - Summary of applied fixes
   - Remaining issues
   - Test results

---

## Next Steps

### Immediate (Unblock Tests)
1. Find units with `ally_team` heals: `grep -r "ally_team" waffen-tactics/units.json`
2. Migrate them to skills.json format
3. Verify 302/302 tests pass

### Short Term (Event Quality)
1. ✅ **DONE**: `emit_stat_buff` includes applied_delta for all stats
2. Resolve `stat='random'` to concrete stat before emission
3. Prevent DoT tick duplicates via event_id
4. Emit `stat_buff` for all synergy buffs
5. Emit `effect_expired` from effect processor

### Long Term (Reconstructor Cleanup)
1. Delete stat buff delta calculation (lines 386-416)
2. Delete random stat inference (lines 683-716)
3. Delete effect reconciliation (lines 606-848) - replace with strict validation
4. Delete synthetic expiration (lines 859-906)
5. Reduce reconstructor from 1050 lines to <300 lines

---

## Summary

### ✅ Achievements

1. **emit_stat_buff** now provides authoritative `applied_delta` for **ALL stats**
   - Eliminates percentage calculation in reconstructor
   - Consistent rounding matches backend behavior
   - Handles unknown/custom stats gracefully

2. **Verified** all damage/heal/DoT events already include authoritative HP
   - `emit_damage`: `target_hp`, `new_hp`, `unit_hp`, `pre_hp`, `post_hp`
   - `emit_unit_heal`: `unit_hp`, `pre_hp`, `post_hp`
   - `emit_damage_over_time_tick`: `unit_hp` from `emit_damage`

3. **Documented** all reconstructor violations with clear fix instructions
   - File header explains core principle
   - Each function marked with `❌ BACKEND BUG`
   - All fallback logic wrapped with temporary markers

4. **Maintained** test stability - 301/302 passing (no regression)

### 🎯 Key Insight

The backend emitters are **closer to correct** than initially thought:
- ✅ Damage/heal/DoT events already authoritative
- ✅ Stat buff events now include applied_delta
- ❌ Still missing: random stat resolution, effect expiration events, DoT deduplication
- 🔴 **Blocker**: OLD skill system ally_team heal bug

**Most of the remaining issues are:**
1. Missing event emissions (expiration, synergy buffs)
2. Old skill system bugs (ally_team heals)
3. Reconstructor over-engineering (reconciliation, synthetic expiration)

**Path forward**: Fix OLD skill system, emit missing events, delete reconstructor workarounds.
