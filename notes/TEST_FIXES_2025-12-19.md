# Test Fixes - December 19, 2025

## Status: 3/4 Tests Fixed ✅

### Tests Fixed:

1. ✅ `test_mana_accumulation_and_skill_casting` - **FIXED**
   - **Issue**: Missing mana_update events when skills were cast
   - **Root Cause**: `_last_mana` tracking was not initialized at combat start, so delta couldn't be computed, and events without deltas were suppressed
   - **Fix**: Initialize `_last_mana` for all units at combat start in [combat_simulator.py:223-227](waffen-tactics/src/waffen_tactics/services/combat_simulator.py#L223-L227)

2. ✅ `test_skill_support_effects_in_combat_emit_heal_buff_shield` - **FIXED**
   - **Issue**: Missing unit_heal events from healing skills
   - **Root Cause**: Units were being reset to max HP before combat, so healing had no effect (can't heal from 100/100 to 100/100)
   - **Fix**: Changed reset logic to only reset dead units (hp <= 0), not partially damaged units in [combat_service.py:426-452](waffen-tactics-web/backend/services/combat_service.py#L426-L452)

3. ✅ `test_heal_buff_shield_mapped_have_names` - **FIXED**
   - Same fix as #2

### Test Still Failing:

4. ❌ `test_10v10_simulation_multiple_seeds` - **STILL FAILING**
   - **Issue**: HP reconstruction from events doesn't match actual simulation HP
   - **Error**: `AssertionError: 444 != 464 : HP mismatch for opponent unit Mrvlook (mrvlook) at seed 5`
   - **Analysis**: Reconstruction has 464 HP, simulation has 444 HP (20 HP difference)
     - Reconstruction HP is HIGHER = Missing damage event OR incorrect damage calculation
   - **Partial Fix Applied**:
     - Removed code that was overwriting `old_hp` and `new_hp` fields in events ([combat_simulator.py:157-160](waffen-tactics/src/waffen_tactics/services/combat_simulator.py#L157-L160))
     - Updated reconstructor to use authoritative `target_hp` from events ([combat_event_reconstructor.py:106-133](waffen-tactics-web/backend/services/combat_event_reconstructor.py#L106-L133))
   - **Status**: Still investigating why 20 HP damage is missing in reconstruction

## Other Code Changes:

- **combat_simulator.py**:
  - Initialize `_last_mana` tracking at combat start
  - Removed code that overwrote `old_hp`/`new_hp` in events

- **combat_service.py**:
  - Fixed unit reset logic to preserve intentionally damaged units

- **combat_event_reconstructor.py**:
  - Use authoritative `target_hp` from events instead of calculating from damage

## Next Steps:

1. Debug seed 5 to find which specific attack/damage event is causing the 20 HP discrepancy
2. Check if there are any skill damage events that aren't being emitted properly
3. Verify that all damage sources (attacks, skills, DOT, etc.) properly emit events with correct `target_hp`
4. Consider adding event sequence validation to detect missing events

## Architecture Notes:

The event reconstruction system is CRITICAL for frontend gameplay. The frontend cannot directly see the combat simulation - it must rebuild the entire game state from the event stream. Any missing or incorrect events will cause desync between what the simulation calculated and what the frontend displays to the user.

**Golden Rule**: Every state change in combat MUST have a corresponding event with authoritative HP values.
