# Combat Desync Root Cause Analysis

## Problem Statement

Test `test_10v10_simulation_multiple_seeds` fails at seed 5 with HP mismatch:
- Simulation: Mrvlook HP = 444
- Reconstruction: Mrvlook HP = 464
- Difference: 20 HP

## Investigation Timeline

### Discovery 1: Single-Seed vs Multi-Seed Behavior

When running seed 5 in ISOLATION:
- ✅ Mrvlook HP matches: sim=0, recon=0

When running seeds 1-5 in SEQUENCE (reusing unit objects):
- ❌ Seed 5 fails: sim=444, recon=464, diff=20

**Key Insight**: The test creates unit objects ONCE and runs multiple simulations with different seeds. Units carry state between runs.

### Discovery 2: Unit Reset Between Seeds

After seed 4:
- Mrvlook HP = 0 (dead)

Before seed 5:
- Mrvlook HP reset to 600 (reset logic: `if hp <= 0: hp = max_hp`)

During seed 5:
- Mrvlook is attacked and dies
- Final HP: sim=0

### Discovery 3: Event Count Mismatch

Seed 5 events targeting Mrvlook:
- Total attack events in stream: 2
- Attack events processed by reconstructor: 0

**The 2 attack events exist but are NOT changing HP in reconstruction!**

### Discovery 4: Wrong `target_hp` Values

The 2 attack events have INCORRECT `target_hp` values:

```
Attack 1: damage=60, target_hp=600  ← WRONG! Should be 540
Attack 2: damage=100, target_hp=600 ← WRONG! Should be 440
```

Both attacks show `target_hp=600`, which is the HP BEFORE any damage was applied!

## Root Cause Hypothesis

The issue is in how `target_hp` is set in attack events. The attack processor ([combat_attack_processor.py:60-70](../../waffen-tactics/src/waffen_tactics/services/combat_attack_processor.py#L60-L70)) emits:

```python
event_callback('attack', {
    ...
    'target_hp': defending_hp[target_idx],  # Should be new HP after damage
    ...
})
```

This `target_hp` value is CORRECT at emission time (HP after damage).

BUT, the wrapped callback in combat_simulator.py has code that OVERWRITES this value:

```python
# Lines 151-155 (REMOVED in recent fix)
if 'target_id' in payload:
    payload['target_hp'] = authoritative_hp  # <-- OVERWRITE!
```

The `authoritative_hp` is looked up from `hp_list[local_idx]` at the time the wrapped callback runs.

## Timeline of Events (Seed 5, Attack 1)

1. **Before attack**: `b_hp[mrvlook_idx] = 600`
2. **Damage calculated**: `damage = 60`
3. **HP updated**: `b_hp[mrvlook_idx] = 600 - 60 = 540` ← HP list updated
4. **Event emitted**: `event_callback('attack', {'target_hp': 540, ...})`
5. **Wrapped callback runs**:
   - Looks up `authoritative_hp = b_hp[mrvlook_idx]`
   - **PROBLEM**: At this point, what is `b_hp[mrvlook_idx]`?
   - If it's 540: `target_hp` should be 540 ✅
   - If it's 600: `target_hp` gets set to 600 ❌

## Why Is `authoritative_hp` Wrong?

**Theory 1**: The HP list lookup is finding the WRONG unit
- Maybe the unit index is off by one?
- Maybe team_a/team_b are swapped?

**Theory 2**: The HP is being looked up BEFORE the damage is applied
- But the attack processor updates HP before calling the callback...
- So this shouldn't be possible

**Theory 3**: There's a timing issue with async/threading
- But combat is single-threaded...

**Theory 4**: The HP list (`self.a_hp` / `self.b_hp`) is NOT the same object as `defending_hp`
- Need to verify if `defending_hp` parameter is passed by reference

## Next Steps

1. Add debug logging to wrapped_callback to see what `authoritative_hp` value is being used
2. Verify that `defending_hp` and `self.b_hp` are the SAME object (not a copy)
3. Check if there's any code that creates a copy of the HP lists
4. Test with a minimal reproduction case

## Code Locations

- Attack emission: [combat_attack_processor.py:60-70](../../waffen-tactics/src/waffen_tactics/services/combat_attack_processor.py#L60-L70)
- Wrapped callback: [combat_simulator.py:72-221](../../waffen-tactics/src/waffen_tactics/services/combat_simulator.py#L72-L221)
- HP list initialization: [combat_simulator.py:66-69](../../waffen-tactics/src/waffen_tactics/services/combat_simulator.py#L66-L69)

## Current Status

- ✅ Fixed: Removed code that overwrote `old_hp` and `new_hp`
- ✅ Fixed: Reconstructor now uses authoritative `target_hp` from events
- ❌ Pending: `target_hp` values in events are still WRONG at seed 5
