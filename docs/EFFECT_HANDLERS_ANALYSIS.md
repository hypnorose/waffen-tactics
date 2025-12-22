# Effect Handlers Analysis - Canonical Emitter Usage

**Date**: 2025-12-20
**Status**: Analysis Complete

---

## Overview

This document analyzes all skill effect handlers to verify they properly use canonical emitters for state mutations, ensuring consistency between backend simulation, event reconstruction, and frontend UI.

---

## ✅ Handlers Using Canonical Emitters

### 1. **BuffHandler** (`effects/buff.py`)

**Status**: ✅ **FULLY CANONICAL**

```python
# Lines 47-58: Uses emit_stat_buff
payload = emit_stat_buff(
    cb,
    recipient=target,
    stat=stat,
    value=value,
    value_type=value_type,
    duration=duration,
    permanent=False,
    source=context.caster,
    side=None,
    timestamp=getattr(context, 'combat_time', None),
)
```

**Benefits**:
- State mutation handled by canonical emitter
- Returns authoritative `applied_delta` in payload
- Resolves `stat: 'random'` at cast time (lines 26-30) for deterministic replay

---

### 2. **ShieldHandler** (`effects/shield.py`)

**Status**: ✅ **FULLY CANONICAL**

```python
# Lines 30-37: Uses emit_shield_applied
payload = emit_shield_applied(
    None,
    recipient=target,
    amount=amount,
    duration=duration,
    source=context.caster,
    timestamp=context.combat_time,
)
```

**Benefits**:
- Shield state updated by canonical emitter
- Consistent event structure

---

### 3. **DoT Tick Processing** (combat_simulator.py)

**Status**: ✅ **FULLY CANONICAL**

```python
# Lines 895-905: DoT tick damage uses emit_damage_over_time_tick
payload = emit_damage_over_time_tick(
    event_callback=event_callback,
    target=unit,
    damage=actual_damage,
    damage_type=damage_type,
    side=side,
    timestamp=time,
    effect_id=effect.get('id'),
    tick_index=tick_index,
    total_ticks=total_ticks,
)

# Lines 913-923: HP list synchronized from unit.hp (set by emitter)
authoritative_hp = int(getattr(unit, 'hp'))
hp_list[i] = max(0, authoritative_hp)
```

**Benefits**:
- `emit_damage_over_time_tick` internally calls `emit_damage` (event_canonicalizer.py:395)
- `emit_damage` mutates `target.hp` (line 593)
- HP list synced from authoritative `unit.hp`
- Event includes authoritative `unit_hp` from `post_hp`
- Removed fallback calculation - now fails loudly if `unit.hp` not set

---

## ⚠️ Handlers NOT Using Canonical Emitters (But Fixed by User)

### 4. **HealHandler** (`effects/heal.py`)

**Status**: ⚠️ **PARTIALLY CANONICAL** (User recently refactored)

**Old behavior** (WRONG):
```python
# Old: Directly mutated target.hp
target.hp = min(max_hp, target.hp + amount)
```

**New behavior** (User's fix):
```python
# Lines 22-24: Calculate new HP without mutation
old_hp = int(getattr(target, 'hp', 0))
max_hp = int(getattr(target, 'max_hp', old_hp))
new_hp = min(max_hp, old_hp + int(amount))

# Lines 33-35: Only mutate for tests/dry-runs (no event_callback)
if getattr(context, 'event_callback', None) is None:
    target.hp = new_hp  # Direct mutation only for tests

# Lines 51-61: Return event with pre_hp and post_hp (NO mutation)
event = ('unit_heal', {
    'unit_id': target.id,
    'unit_name': target.name,
    'healer_id': context.caster.id,
    'healer_name': context.caster.name,
    'amount': actual_heal,
    'pre_hp': old_hp,
    'post_hp': new_hp,
    'unit_max_hp': max_hp,
    'timestamp': context.combat_time,
})
```

**Issue**:
- ❌ Does NOT call `emit_unit_heal` canonical emitter
- ❌ Returned event lacks `unit_hp` field (added later by backfill at combat_simulator.py:158)
- ❌ HP list NOT updated by handler (updated separately in combat_simulator.py:719)

**Why This Causes HP Desync**:

1. Skill execution flow (combat_simulator.py lines 712-724):
   ```python
   # Line 717: HP list updated BEFORE emitting
   old_hp = target_hp_list[apply_idx]
   target_hp_list[apply_idx] = min(getattr(target, 'max_hp', old_hp + amount), target_hp_list[apply_idx] + amount)

   # Line 720-723: Then emit_unit_heal called with current_hp parameter
   if event_callback:
       from .event_canonicalizer import emit_unit_heal
       target_obj = (defending_team_full[apply_idx] if defending_team_full and apply_idx < len(defending_team_full) else target)
       emit_unit_heal(event_callback, target_obj, caster, amount, side=side, timestamp=time, current_hp=old_hp)
   ```

2. But `HealHandler` returns events DIRECTLY without going through this flow!
   - `HealHandler` emits event with `pre_hp` and `post_hp`
   - Event backfill at line 158 adds `unit_hp` from HP list
   - BUT HP list is NOT updated by `HealHandler`
   - So `unit_hp` gets stale value from HP list!

**Recommended Fix**:

Make `HealHandler` use `emit_unit_heal`:

```python
def execute(self, effect: Effect, context: SkillExecutionContext, target) -> List[Dict[str, Any]]:
    """Execute heal effect"""
    amount = effect.params.get('amount', 0)

    if amount <= 0:
        return []

    # Get current HP
    old_hp = int(getattr(target, 'hp', 0))
    max_hp = int(getattr(target, 'max_hp', old_hp))

    # Use canonical emitter to apply heal and emit event
    from waffen_tactics.services.event_canonicalizer import emit_unit_heal

    cb = getattr(context, 'event_callback', None)
    payload = emit_unit_heal(
        cb,
        target=target,
        healer=context.caster,
        amount=amount,
        side=None,
        timestamp=context.combat_time,
        current_hp=old_hp,  # Pass current HP so emitter can calculate new HP
    )

    if cb:
        return []  # Event already emitted by canonical emitter
    return [('unit_heal', payload)]
```

---

### 5. **DamageHandler** (`effects/damage.py`)

**Status**: ⚠️ **NOT USING CANONICAL EMITTER**

**Current behavior**:
```python
# Lines 26-27: Calculate new HP without mutation
old_hp = int(getattr(target, 'hp', 0))
new_hp = max(0, old_hp - int(actual_damage))

# Lines 30-31: Only mutate for tests
if getattr(context, 'event_callback', None) is None:
    target.hp = new_hp

# Lines 48-60: Return event with pre_hp and post_hp
event = ('unit_attack', {
    'attacker_id': context.caster.id,
    'attacker_name': context.caster.name,
    'target_id': target.id,
    'target_name': target.name,
    'damage': actual_damage,
    'damage_type': damage_type,
    'pre_hp': old_hp,
    'post_hp': new_hp,
    'unit_hp': new_hp,  # ✅ Includes unit_hp
    'is_skill': True,
    'timestamp': context.combat_time,
})
```

**Issue**:
- ❌ Does NOT call `emit_damage` canonical emitter
- ✅ BUT includes `unit_hp` field in event, so less likely to cause desync
- ⚠️ Still doesn't go through canonical damage path (no shield handling, no death detection)

**Recommended Fix**:

Make `DamageHandler` use `emit_damage`:

```python
def execute(self, effect: Effect, context: SkillExecutionContext, target) -> List[Dict[str, Any]]:
    """Execute damage effect"""
    amount = effect.params.get('amount', 0)
    damage_type = effect.params.get('damage_type', 'physical')

    if amount <= 0:
        return []

    # Use canonical emitter
    from waffen_tactics.services.event_canonicalizer import emit_damage

    cb = getattr(context, 'event_callback', None)
    payload = emit_damage(
        cb,
        attacker=context.caster,
        target=target,
        raw_damage=amount,
        shield_absorbed=0,
        damage_type=damage_type,
        side=None,
        timestamp=context.combat_time,
        cause='skill',
        emit_event=True,
    )

    if cb:
        return []  # Event already emitted
    return [('attack', payload)]
```

---

### 6. **DamageOverTimeHandler** (`effects/damage_over_time.py`)

**Status**: ✅ **CORRECT PATTERN** (applies effect, doesn't deal damage directly)

**Behavior**:
```python
# Lines 34-45: Creates DoT effect object
dot_effect = {
    'id': dot_id,
    'type': 'damage_over_time',
    'damage': damage,
    'damage_type': damage_type,
    'interval': interval,
    'ticks_remaining': ticks,
    'total_ticks': ticks,
    'next_tick_time': next_tick,
    'expires_at': expires_at,
    'source': f"skill_{context.caster.id}"
}

# Lines 48-50: Adds effect to target
if not hasattr(target, 'effects'):
    target.effects = []
target.effects.append(dot_effect)

# Lines 55-69: Emits damage_over_time_applied event
```

**Why This Is Correct**:
- ✅ Does NOT deal damage directly
- ✅ Only adds DoT effect to target's effects list
- ✅ Actual damage ticks are handled by `combat_simulator.py` using `emit_damage_over_time_tick`
- ✅ Each tick goes through canonical `emit_damage` path

---

## Frontend UI Consistency

### Current Issues in `applyEvent.ts`:

#### 1. ⚠️ **`unit_heal` handler priority wrong** (lines 319-340)

**Current**:
```typescript
if (event.amount !== undefined) {
  // ❌ WRONG: Incremental update (adds amount to current HP)
  const updateFn = (u: Unit) => ({ ...u, hp: Math.min(u.max_hp, u.hp + event.amount!) })
  // ...
} else if (event.unit_hp !== undefined) {
  // ✅ CORRECT: Authoritative update
  newHp = event.unit_hp
  // ...
}
```

**Should be**:
```typescript
// Priority 1: Use authoritative HP if available
if (event.unit_hp !== undefined) {
  newHp = event.unit_hp
} else if (event.new_hp !== undefined) {
  newHp = event.new_hp
} else if (event.post_hp !== undefined) {
  newHp = event.post_hp
} else if (event.amount !== undefined) {
  // Priority 2: Fallback to incremental
  const updateFn = (u: Unit) => ({ ...u, hp: Math.min(u.max_hp, u.hp + event.amount!) })
  // ...
}
```

**Why**: Should prefer authoritative values over calculated values, matching reconstructor behavior.

---

#### 2. ✅ **Other handlers are correct**:

- `attack`: Uses authoritative `target_hp` ✅
- `damage_over_time_tick`: Uses authoritative `unit_hp` ✅
- `mana_update`: Prefers `current_mana` over `amount` ✅
- `stat_buff`: Calculates delta correctly ✅

---

## Summary Table

| Handler | Uses Canonical Emitter? | Mutates State? | Includes unit_hp? | Status |
|---------|-------------------------|----------------|-------------------|--------|
| BuffHandler | ✅ `emit_stat_buff` | ✅ Via emitter | ✅ | CORRECT |
| ShieldHandler | ✅ `emit_shield_applied` | ✅ Via emitter | ✅ | CORRECT |
| DamageHandler | ❌ No | ⚠️ Only in tests | ✅ | NEEDS FIX |
| HealHandler | ❌ No | ⚠️ Only in tests | ❌ (backfilled) | NEEDS FIX |
| DamageOverTimeHandler | ✅ Applies effect only | ❌ (correct) | N/A | CORRECT |
| DoT Tick Processing | ✅ `emit_damage_over_time_tick` | ✅ Via emitter | ✅ | CORRECT |

---

## Action Items

### Priority 1: Fix HealHandler

**Issue**: HP desync in 5 seeds (205, 242, 315, 394, 569) caused by:
1. `HealHandler` not using `emit_unit_heal`
2. Event backfill getting stale `unit_hp` from HP list
3. HP list not updated by `HealHandler`

**Fix**: Make `HealHandler.execute()` call `emit_unit_heal` with `current_hp` parameter.

### Priority 2: Fix DamageHandler

**Issue**: Bypasses canonical damage path (no shield handling, death detection)

**Fix**: Make `DamageHandler.execute()` call `emit_damage`.

### Priority 3: Fix UI heal event priority

**Issue**: UI prioritizes incremental `amount` over authoritative `unit_hp`

**Fix**: Reorder checks in `applyEvent.ts` lines 319-340 to prefer authoritative fields.

---

## Conclusion

**Current State**:
- ✅ DoT tick damage: FULLY canonical via `emit_damage_over_time_tick`
- ✅ Buffs: FULLY canonical via `emit_stat_buff`
- ✅ Shields: FULLY canonical via `emit_shield_applied`
- ❌ Skill heals: NOT canonical (causes HP desync)
- ❌ Skill damage: NOT canonical (potential issues)

**All unit state changes SHOULD go through canonical emitters to ensure**:
1. Authoritative HP values in events
2. HP list synchronization
3. Consistent behavior across simulation, reconstruction, and UI
4. Single source of truth for state mutations

**Next Steps**:
1. Fix `HealHandler` to use `emit_unit_heal`
2. Fix `DamageHandler` to use `emit_damage`
3. Test all 5 failing seeds pass
4. Fix UI event priority
5. Document fixes in CANONICALIZER_MIGRATION.md
