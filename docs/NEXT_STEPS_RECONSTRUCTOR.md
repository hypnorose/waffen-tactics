# Next Steps: Fixing Reconstructor HP Desyncs

**Date**: 2025-12-20
**Status**: IN PROGRESS
**Issue**: 5 out of 400 seeds failing with HP mismatches

---

## Problem Summary

Test `test_10v10_simulation_multiple_seeds` shows 5 seeds failing (seeds 205, 242, 315, 394, 569) with HP mismatches like:

```
246 != 286 : HP mismatch for player unit Mrozu (mrozu) at seed 205
138 != 188 : HP mismatch for opponent unit xntentacion (xntentacion) at seed 242
607 != 547 : HP mismatch for player unit Stalin (stalin) at seed 315
```

Reconstructed HP is **consistently different** from authoritative snapshot HP, indicating events are missing authoritative HP values.

---

## Root Cause

Per [RECONSTRUCTOR_ARCHITECTURE_VIOLATIONS.md](./RECONSTRUCTOR_ARCHITECTURE_VIOLATIONS.md), the reconstructor has fallback logic at lines 263-270:

```python
# combat_event_reconstructor.py:263-270
if 'unit_hp' in event_data:
    unit_dict['hp'] = event_data.get('unit_hp')
elif 'target_hp' in event_data:
    unit_dict['hp'] = event_data.get('target_hp')
elif 'new_hp' in event_data:
    unit_dict['hp'] = event_data.get('new_hp')
else:
    # ❌ FALLBACK: Computing HP locally
    unit_dict['hp'] = max(0, unit_dict['hp'] - damage)
```

When backend emits DoT ticks or damage events **without authoritative HP**, the reconstructor computes `hp -= damage` locally. This computation may not match backend due to:
- Overkill protection
- Min HP limits
- Rounding differences
- Shield interactions

---

## Immediate Fixes Required

### Fix #1: Ensure ALL damage events include authoritative HP

**Files to check**:
1. `event_canonicalizer.py` - `emit_damage` function
2. All DoT tick emission code
3. Skill damage emission code

**Action**:
```python
# EVERY damage event must include unit_hp:
payload = {
    ...
    'target_hp': target.hp,  # or 'unit_hp': target.hp
    ...
}
```

### Fix #2: Remove fallback calculation from reconstructor

After backend is fixed, change reconstructor to **fail loudly**:

```python
# combat_event_reconstructor.py:263-270
if 'unit_hp' in event_data:
    unit_dict['hp'] = event_data.get('unit_hp')
elif 'target_hp' in event_data:
    unit_dict['hp'] = event_data.get('target_hp')
elif 'new_hp' in event_data:
    unit_dict['hp'] = event_data.get('new_hp')
else:
    # ❌ ERROR instead of fallback
    raise ValueError(f"damage_over_time_tick event missing authoritative HP: {event_data}")
```

---

## Investigation Plan

1. ✅ Run failing test and capture HP mismatches
2. Pick one failing seed (e.g., seed 205)
3. Run that seed with verbose logging
4. Find the exact event where HP diverges
5. Check if that event includes `unit_hp` / `target_hp` / `new_hp`
6. If missing, trace back to find which emitter is not including it
7. Fix the emitter
8. Verify all 5 seeds pass

---

## Expected Outcome

After fixes:
- All damage/DoT events include authoritative HP
- Reconstructor never uses fallback calculation
- All 400 seeds pass reconstruction validation
- HP desyncs eliminated

---

**Next Action**: Investigate seed 205 to find which event is missing HP
