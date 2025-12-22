# Canonical Emitter Fixes - Session Summary

## Overview
This session focused on ensuring all skill effect handlers use canonical emitters for state mutations, fixing HP desync issues in event replay validation.

## Changes Made

### 1. HealHandler - Now Uses `emit_unit_heal` ✅
**File**: `waffen-tactics/src/waffen_tactics/services/effects/heal.py`

**Before**: Manually created heal events without using canonical emitter
**After**: Calls `emit_unit_heal()` with `current_hp` parameter

```python
# Get current HP before heal
old_hp = int(getattr(target, 'hp', 0))

# Use canonical emitter to apply heal and emit event
cb = getattr(context, 'event_callback', None)
payload = emit_unit_heal(
    cb,
    target=target,
    healer=context.caster,
    amount=amount,
    side=None,
    timestamp=getattr(context, 'combat_time', None),
    current_hp=old_hp,  # Pass current HP for authoritative calculation
)
```

**Impact**:
- ✅ Ensures `unit.hp` is mutated by emitter
- ✅ Events contain authoritative `unit_hp`, `pre_hp`, `post_hp` fields
- ✅ HP values are correctly synchronized

### 2. DamageHandler - Now Uses `emit_damage` ✅
**File**: `waffen-tactics/src/waffen_tactics/services/effects/damage.py`

**Before**: Manually created damage events without canonical emitter
**After**: Calls `emit_damage()` and emits as `unit_attack` to mark skill damage

```python
# Use canonical emitter to apply damage (HP mutation + shield handling)
payload = emit_damage(
    cb,
    attacker=context.caster,
    target=target,
    raw_damage=amount,
    shield_absorbed=0,
    damage_type=damage_type,
    side=None,
    timestamp=getattr(context, 'combat_time', None),
    cause='skill',
    emit_event=False,  # We emit manually as unit_attack
)

# Add is_skill marker and emit as unit_attack
payload['is_skill'] = True
if cb:
    cb('unit_attack', payload)
```

**Impact**:
- ✅ Ensures proper shield handling via canonical emitter
- ✅ Ensures death detection (`unit_died` events)
- ✅ Events marked with `is_skill: True`
- ✅ Emitted as `unit_attack` (not `attack`) to distinguish skill damage

### 3. UI Event Priority Fix ✅
**File**: `waffen-tactics-web/src/hooks/combat/applyEvent.ts`

**Before**: Prioritized incremental update (`event.amount`) over authoritative HP
**After**: Prioritizes authoritative HP fields first

```typescript
case 'unit_heal':
  if (event.unit_hp !== undefined) {
    newHp = event.unit_hp  // ✅ Authoritative first
  } else if (event.post_hp !== undefined) {
    newHp = event.post_hp
  } else if (event.new_hp !== undefined) {
    newHp = event.new_hp
  } else if (event.amount !== undefined) {
    // Fallback: incremental update
    const updateFn = (u: Unit) => ({ ...u, hp: Math.min(u.max_hp, u.hp + event.amount!) })
  }
```

**Impact**:
- ✅ UI now matches reconstructor behavior
- ✅ Authoritative HP values take precedence over deltas

### 4. TypeScript Type Definitions ✅
**File**: `waffen-tactics-web/src/hooks/combat/types.ts`

Added missing HP fields to CombatEvent interface:
```typescript
post_hp?: number  // Authoritative HP after event
pre_hp?: number   // HP before event
new_hp?: number   // Alternative authoritative HP field (legacy)
```

### 5. Backend Reconstructor Priority Fix ✅
**File**: `waffen-tactics-web/backend/services/combat_event_reconstructor.py`

Added `post_hp` to priority chain:
```python
if 'unit_hp' in event_data and event_data.get('unit_hp') is not None:
    authoritative_hp = event_data.get('unit_hp')
elif 'post_hp' in event_data and event_data.get('post_hp') is not None:
    authoritative_hp = event_data.get('post_hp')  # ✅ Added
elif 'target_hp' in event_data and event_data.get('target_hp') is not None:
    authoritative_hp = event_data.get('target_hp')
```

### 6. HP Synchronization Improvements ✅
**File**: `waffen-tactics/src/waffen_tactics/services/combat_simulator.py`

Added HP list synchronization from `unit.hp` before state snapshots:

```python
# CRITICAL: Sync HP lists from unit.hp before snapshot
# Canonical emitters mutate unit.hp directly
for i, u in enumerate(team_a):
    a_hp[i] = max(0, int(getattr(u, 'hp', a_hp[i])))
for i, u in enumerate(team_b):
    b_hp[i] = max(0, int(getattr(u, 'hp', b_hp[i])))
```

**Impact**:
- ✅ Ensures snapshots reflect HP mutations from canonical emitters
- ✅ Prevents stale HP values in state_snapshot events

## Test Results

### 📊 Overall: 280/281 Tests Passing (99.6%)

**Before this session**: 11 tests failing
**After this session**: 1 test failing
**Fixed**: 10 tests ✅

### ✅ All Skill Tests Pass
- `test_skill_effect_events.py`: 4/4 PASSED
- `test_comprehensive_system.py::TestSkillParserAndEffects`: 21/21 PASSED
- `test_delayed_skills_events.py`: 2/2 PASSED
- `test_skill_effects.py`: 3/3 PASSED
- `test_skills_in_combat.py`: 4/4 PASSED
- `test_sse_mapping.py`: 3/3 PASSED

### ⚠️ Remaining Issue: OLD Skill System `ally_team` Heals

**Test**: `test_10v10_simulation_multiple_seeds` - 8 seeds failing with HP desyncs
**Status**: Expected failure - this is an architectural limitation of the old skill system

**Root Cause**:
The OLD skill system (fallback path in `combat_simulator.py` lines 612-768) does NOT properly handle `ally_team` target type. Units using the old inline skill format (dict with `effects` list) that have `target: "ally_team"` experience HP synchronization issues.

**Example**:
- Grzałcia has skill: `{"name": "Healing Aura", "effects": [{"type": "heal", "target": "ally_team", "amount": 40}]}`
- The old system doesn't recognize `ally_team` as a valid target spec
- Heal ends up updating wrong HP list or not at all

**Solution**:
Migrate all units to NEW skill format in `skills.json`. Units using the new format go through `skill_executor` which correctly uses `HealHandler` → `emit_unit_heal`.

**Units Still Using Old Format**:
- Grzałcia (Healing Aura with ally_team)
- Any other units with inline skill definitions in `units.json`

## Summary

✅ **Completed**:
1. HealHandler uses `emit_unit_heal` canonical emitter
2. DamageHandler uses `emit_damage` canonical emitter
3. Skill damage correctly emits `unit_attack` events with `is_skill: True`
4. UI event application prioritizes authoritative HP
5. Backend reconstructor prioritizes authoritative HP
6. HP synchronization before snapshots
7. All 37 skill-related tests pass

⚠️ **Remaining Work**:
- Migrate units with `ally_team` heals from old skill format to `skills.json`
- Alternative: Add `ally_team` support to old skill system (not recommended, old system is being phased out)

## Files Modified

### Backend (Python)
1. `waffen-tactics/src/waffen_tactics/services/effects/heal.py`
2. `waffen-tactics/src/waffen_tactics/services/effects/damage.py`
3. `waffen-tactics/src/waffen_tactics/services/combat_simulator.py`
4. `waffen-tactics-web/backend/services/combat_event_reconstructor.py`

### Frontend (TypeScript)
1. `waffen-tactics-web/src/hooks/combat/types.ts`
2. `waffen-tactics-web/src/hooks/combat/applyEvent.ts`

## Verification

Run tests to verify fixes:
```bash
# Core skill tests
cd waffen-tactics
source bot_venv/bin/activate
python -m pytest tests/test_skill_effect_events.py -v
python -m pytest tests/test_comprehensive_system.py::TestSkillParserAndEffects -v

# Web backend tests
cd waffen-tactics-web/backend
source venv/bin/activate
python -m pytest tests/test_skill_effects.py tests/test_skills_in_combat.py tests/test_sse_mapping.py -v
```

All should pass ✅
