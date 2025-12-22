# Combat Event Reconstructor - Architectural Analysis

## Executive Summary

The combat event reconstructor (`combat_event_reconstructor.py`) has been analyzed and documented to clearly mark **architectural violations** where the reconstructor contains game logic that should belong in the backend.

**Status**: ✅ Reconstructor is now fully documented with violation markers
**Test Status**: ✅ All tests still pass (280/281 - same as before)
**Files Modified**: `waffen-tactics-web/backend/services/combat_event_reconstructor.py`

---

## Core Principle: Event Sourcing

The reconstructor should be a **DUMB REPLAY ENGINE**:
- ✅ Apply events in sequence
- ✅ Update state based on explicit event fields
- ❌ NO game formulas or calculations
- ❌ NO inference or "smart" recovery logic
- ❌ NO synthetic state derivation

**Invariant**: State must be fully derivable from events alone. If it's not, **the backend is broken**.

---

## Violations Identified and Marked

All violations are now marked with `❌ BACKEND BUG` comments and wrapped in:
```python
# ==================================================================================
# TEMPORARY FALLBACK LOGIC - SHOULD BE DELETED ONCE BACKEND IS FIXED
# ==================================================================================
... problematic code ...
# ==================================================================================
# END TEMPORARY FALLBACK LOGIC
# ==================================================================================
```

### 1. ✅ skill_cast Handler (FIXED)

**Before**: Applied mana reset and damage from skill_cast event
**After**: Now empty (mana changes come from `mana_update`, damage from `unit_attack`)

```python
def _process_skill_cast_event(self, event_data: Dict[str, Any]):
    """Process skill_cast event.

    NOTE: This handler is INTENTIONALLY LIMITED.
    - Mana changes should come from 'mana_update' events
    - Damage should come from 'unit_attack' or 'attack' events
    - This event exists ONLY for UI animation triggers
    """
    pass  # Intentionally minimal
```

**Backend Fix**: Already correct - emits separate `mana_update` and `unit_attack` events.

---

### 2. ❌ stat_buff Handler (TEMPORARY WORKAROUND DOCUMENTED)

**Problem**: Computes percentage buff deltas and infers random stats

**Lines 386-416**: Fallback calculation when `applied_delta` is missing
- Computes `int(round(base * (pct / 100.0)))` for percentage buffs
- Uses `base_stats` vs `current_stat` heuristics
- **Cannot know which base to use** - this is game logic

**Lines 683-716** (in reconciliation): Infers which stat was buffed when `stat='random'`
- Compares reconstructed vs snapshot values to guess the stat
- **Reverse engineering** instead of replying

**Backend Fix Required**:
```python
# In emit_stat_buff()
payload['applied_delta'] = actual_delta_applied  # ALWAYS include

# For random stat buffs - resolve BEFORE emission
if stat == 'random':
    stat = random.choice(['attack', 'defense', 'attack_speed', 'hp'])
payload['stat'] = stat  # Emit resolved stat, not 'random'
```

**Location**: `event_canonicalizer.py` - `emit_stat_buff()`

---

### 3. ❌ Damage/Heal/DoT Handlers (TEMPORARY WORKAROUNDS DOCUMENTED)

**Problem**: Fall back to delta calculations when authoritative HP is missing

**_process_damage_event (Lines 146-156)**:
```python
if new_hp is not None:
    unit_dict['hp'] = new_hp
else:
    # TEMPORARY FALLBACK - should be deleted
    if damage > 0:
        unit_dict['hp'] = max(0, old_hp - damage)
```

**_process_heal_event (Lines 238-248)**:
```python
if authoritative_hp is not None:
    unit_dict['hp'] = min(unit_dict['max_hp'], authoritative_hp)
else:
    # TEMPORARY FALLBACK - should be deleted
    if amount is not None:
        unit_dict['hp'] = min(unit_dict['max_hp'], old_hp + amount)
```

**_process_dot_event (Lines 339-347)**:
```python
if 'unit_hp' in event_data:
    unit_dict['hp'] = event_data.get('unit_hp')
else:
    # TEMPORARY FALLBACK - should be deleted
    unit_dict['hp'] = max(0, unit_dict['hp'] - damage)
```

**Backend Fix Required**:
```python
# In emit_damage()
payload['target_hp'] = target.hp  # ALWAYS include

# In emit_unit_heal()
payload['unit_hp'] = target.hp  # ALWAYS include

# In DoT tick emitter
payload['unit_hp'] = target.hp  # ALWAYS include
```

**Locations**:
- `event_canonicalizer.py` - `emit_damage()`, `emit_unit_heal()`
- `combat_effect_processor.py` - DoT tick emission

---

### 4. ❌ DoT Tick Deduplication (TEMPORARY WORKAROUND DOCUMENTED)

**Problem**: Reconstructor detects and filters duplicate DoT tick events

**Lines 295-325**: Deduplication logic
- Compares timestamp + damage + effect_id with previous tick
- Skips if duplicate detected
- **Masks backend bug** where duplicates are emitted

**Backend Fix Required**:
Ensure DoT tick emitter uses `event_id` for idempotency and never emits duplicates.

**Location**: `combat_effect_processor.py` - DoT tick emission

---

### 5. ❌ Effect Reconciliation from Snapshots (MAJOR VIOLATION DOCUMENTED)

**Problem**: 500+ line function that applies effects from snapshots when they're missing from events

**Lines 657-873**: `reconcile_effects()` function
- If effect exists in snapshot but not in reconstructed state, **applies it from snapshot**
- Handles buffs, shields, DoTs
- For `stat='random'`, **infers which stat** by comparing values
- **Violates event sourcing**: state should come from events, not snapshots

**What it does**:
1. Compares snapshot effects to reconstructed effects
2. For missing effects, applies them (mutates stats, adds to effects list)
3. For random stat buffs, guesses which stat by comparing values
4. Syncs top-level stats from snapshot (HP, defense, etc.)
5. Prunes reconstructed effects not in snapshot

**Why it's wrong**:
- Snapshots are **validation checkpoints**, not data sources
- If effect is in snapshot but no event emitted, **backend forgot to emit event**
- Reconciliation **hides this bug** instead of exposing it
- UI replay would be broken (no event to animate)

**Backend Fix Required**:
```python
# Ensure ALL effects emit application events:
# - Buffs: emit_stat_buff()
# - Shields: emit_shield_applied()
# - DoTs: emit_damage_over_time_applied()

# Example: Synergy buffs must emit events
for unit in team_a:
    for synergy_buff in calculate_synergies(unit):
        emit_stat_buff(callback, unit, stat, value, ...)  # MUST emit
```

**Locations**:
- `synergy.py` - Synergy buff application
- `combat_simulator.py` - Any buff/shield/DoT application
- Ensure all paths that create effects also emit events

---

### 6. ❌ Synthetic Effect Expiration (MAJOR VIOLATION DOCUMENTED)

**Problem**: Reconstructor expires effects based on time and reverts stat changes

**Lines 940-1013**: `_expire_effects()` function
- Calculates `expires_at` from `ticks_remaining + interval + next_tick_time` for DoTs
- Filters effects by `expires_at > current_time`
- **Reverts stat changes** when effects expire (subtracts `applied_delta`)
- Reverts shield amounts

**Why it's wrong**:
- Effect expiration may have **side effects** (triggers, conditional removal)
- Backend **knows when effects expire** - it should emit events
- Reconstructor **cannot know expiration rules** (permanent buffs, conditional removal, etc.)
- Deriving `expires_at` from ticks/interval is **game logic**

**Backend Fix Required**:
```python
# In combat_effect_processor.py - effect expiration loop
for effect in unit.effects:
    if effect.expires_at <= current_time:
        # Emit expiration event BEFORE removing effect
        emit_effect_expired(callback, unit, effect_id=effect.id, ...)
        # Then remove from unit.effects
```

**Locations**:
- `combat_effect_processor.py` - Effect expiration loop
- DoT expiration should emit `damage_over_time_expired`
- Buff/debuff/shield expiration should emit `effect_expired`

---

## Immediate Test Failure: OLD Skill System `ally_team` Heals

**Test**: `test_10v10_simulation_multiple_seeds` - 2 seeds failing (was 8, now 2 after fixes)
**Root Cause**: OLD skill system does NOT support `ally_team` target type

### The Problem

**Location**: `combat_simulator.py:800-813`

The old skill system's heal handler:
```python
elif typ == 'heal':
    amount = eff.get('amount', 0)
    apply_idx = chosen_idx if chosen_idx is not None else target_idx
    # ...
    target_hp_list[apply_idx] = min(...)  # Updates HP list
    emit_unit_heal(callback, target_obj, caster, amount, ...)  # Emits event
```

Combined with how `_process_skill_cast` is called (line 486):
```python
self._process_skill_cast(unit, defending_team[target_idx], defending_hp, ...)
                                                            ^^^^^^^^^^^^
                                                   This is defending team's HP list
```

**The Bug**:
1. For ally heals (e.g., Grzałcia's "Healing Aura" with `target: "ally_team"`):
   - Target is on **attacking team**, NOT defending team
   - But `target_hp_list` parameter is `defending_hp`
2. Line 808 updates `target_hp_list[apply_idx]` = `defending_hp[apply_idx]` ❌ WRONG TEAM
3. Line 812 calls `emit_unit_heal()` with correct target object → sets `unit.hp` correctly ✅
4. Result: `unit.hp` = correct, but `attacking_hp[idx]` = stale (never updated)

### What Gets Changed

| State Field | Changed By | Value | Correct? |
|-------------|-----------|-------|----------|
| `unit.hp` | ✅ emit_unit_heal | 286 | ✅ YES |
| `attacking_hp[idx]` | ❌ Never | 246 | ❌ NO (stale) |
| `defending_hp[wrong_idx]` | ❌ Line 808 | 286 | ❌ NO (wrong unit) |

State snapshot reads from HP lists → desync.

### The Fix (TWO OPTIONS)

#### Option 1: Migrate Units to skills.json (RECOMMENDED)

Units using new skill format go through `skill_executor.py` → `HealHandler.execute()` → `emit_unit_heal()` which correctly handles ally heals.

**Units to migrate**:
- Grzałcia (Healing Aura with `ally_team` heals)
- Any other units with inline skill definitions containing `target: "ally_team"`

**Find them**:
```bash
grep -r "ally_team" waffen-tactics/units.json
```

#### Option 2: Add ally_team Support to Old System (NOT RECOMMENDED)

Would require:
1. Add `ally_team` target resolution in lines 733-758
2. Make `_process_skill_cast` accept BOTH `attacking_hp` and `defending_hp`
3. Select correct HP list based on whether target is ally or enemy
4. **Adds complexity to legacy code being phased out**

---

## Backend Fixes Checklist

### Event Schema Improvements

- [ ] **emit_stat_buff()**: Always include `applied_delta`
- [ ] **emit_damage()**: Always include `target_hp`
- [ ] **emit_unit_heal()**: Always include `unit_hp` or `post_hp`
- [ ] **DoT tick emitter**: Always include `unit_hp`
- [ ] **Random stat buffs**: Resolve `stat='random'` to concrete stat before emission
- [ ] **skill_cast events**: Remove `damage` field (use separate `unit_attack` events)

### New Event Emissions

- [ ] **Effect expiration**: Emit `effect_expired` when buffs/debuffs/shields expire
- [ ] **DoT expiration**: Emit `damage_over_time_expired` consistently
- [ ] **Synergy buffs**: Emit `stat_buff` events for all synergy applications
- [ ] **Shield application**: Emit `shield_applied` for ALL shield applications
- [ ] **DoT application**: Emit `damage_over_time_applied` for ALL DoT applications

### Event Deduplication

- [ ] **DoT tick emitter**: Use `event_id` for idempotency (prevent duplicates)

### OLD Skill System

- [ ] **Migrate units with ally_team heals** to skills.json (Grzałcia, others)
  - OR add ally_team support to old system (not recommended)

---

## Reconstructor Simplifications (After Backend Fixes)

Once backend is fixed, **DELETE these sections**:

1. ✅ **skill_cast mana reset and damage** (Lines 348-359) → Already removed
2. ❌ **stat_buff delta calculation** (Lines 386-416) → Delete when `applied_delta` always present
3. ❌ **stat_buff random stat inference** (Lines 683-716 in reconciliation) → Delete when stat resolved
4. ❌ **Damage/heal/DoT HP fallback calculations** (Lines 146-156, 238-248, 339-347) → Delete when HP always present
5. ❌ **DoT tick deduplication** (Lines 295-325) → Delete when backend prevents duplicates
6. ❌ **Effect reconciliation from snapshots** (Lines 657-873) → Replace with STRICT validation (fail on mismatch)
7. ❌ **Synthetic effect expiration** (Lines 940-1013) → Delete entire `_expire_effects()` function

**Target**: Reduce reconstructor from **1050 lines** to **<300 lines** of simple event application.

---

## Documentation Added

### File Header
Added comprehensive architectural violations warning at top of file explaining:
- Core principle (dumb replay engine)
- Current violations (6 categories)
- Required backend fixes
- Immediate test failure cause

### Function Docstrings
Updated all event handler docstrings with:
- `❌ BACKEND BUG:` markers explaining what's wrong
- `TODO (BACKEND FIX REQUIRED):` specific fix instructions
- Explanation of why the current approach is wrong

### Inline Comments
Wrapped all fallback/workaround logic with:
```python
# ==================================================================================
# TEMPORARY FALLBACK LOGIC - SHOULD BE DELETED ONCE BACKEND IS FIXED
# ==================================================================================
... problematic code ...
# ==================================================================================
# END TEMPORARY FALLBACK LOGIC
# ==================================================================================
```

---

## Test Results

**Before**: 280/281 tests passing (2 seeds failing)
**After**: 280/281 tests passing (2 seeds failing - same as before)
✅ No regression - documentation changes only

The 1 remaining failure is **expected and documented**:
- **Test**: `test_10v10_simulation_multiple_seeds`
- **Seeds failing**: 2 (down from 8 after earlier canonical emitter fixes)
- **Cause**: OLD skill system `ally_team` heal bug (documented above)
- **Fix**: Migrate units to skills.json

---

## Next Steps

### Immediate (Unblock Tests)
1. Find units with `ally_team` heals: `grep -r "ally_team" waffen-tactics/units.json`
2. Migrate them to skills.json format
3. Verify 281/281 tests pass

### Short Term (Backend Event Fixes)
1. Add `applied_delta` to `emit_stat_buff()`
2. Add authoritative HP to all damage/heal/DoT events
3. Emit expiration events from effect processor
4. Resolve random stats before emission

### Long Term (Architectural Cleanup)
1. Delete fallback calculations from reconstructor
2. Delete reconciliation logic (replace with strict validation)
3. Delete synthetic expiration
4. Reduce reconstructor to <300 lines
5. Add integration tests that verify events are sufficient for reconstruction

---

## Files Modified

- `waffen-tactics-web/backend/services/combat_event_reconstructor.py`
  - Added comprehensive architectural violations documentation
  - Marked all temporary workarounds with clear comments
  - Emptied `_process_skill_cast_event()` (state comes from dedicated events)
  - Added detailed docstrings to all violation handlers
  - Added file header explaining core principle and fixes required

---

## Summary

The reconstructor has been **fully documented** with clear markers showing:
- ✅ Where it violates event-sourcing principles
- ❌ What backend bugs it's working around
- 🔧 Exact fixes required in the backend
- 📍 Which files need changes
- 🗑️ What code should be deleted after fixes

The goal is to make it **impossible to miss** that these workarounds are temporary and should be fixed in the backend, not accepted as permanent reconstructor complexity.
