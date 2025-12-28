# Session summary — Seed 300 (compact)

## Goal
- Diagnose and fix mana desync: simulation shows `puszmen12.mana = 75` while reconstructor/snapshots show `70` (seed=300).

## Reproduction
- Test run used: `pytest -q .../tests/test_combat_service.py -k seed_300 -s` (single failing test).
- Full run output saved to: `/tmp/seed300_debug.txt` (contains event stream, instrumented setter outputs, and stacks).

## Key findings
- Instrumented `CombatUnit.mana` setter to log every write and printed short stack traces.
- Located anomalous direct write: `DEBUG MANA SET: unit=puszmen12 old=70 new=75`.
- That write occurs during death-processing / attack handling context:
  - Stack (top project frames):
    - `combat_simulator.py: simulate -> _process_team_attacks`
    - `combat_attack_processor.py: _process_team_attacks -> emit_mana_change`
    - `event_canonicalizer.py: emit_mana_change -> recipient.mana = new_val`
    - `combat_unit.py: mana.setter` (logged stack)
- The canonicalizer `emit_mana_change` intentionally mutates `recipient.mana` (calls `recipient.mana = new_val`), so the write is expected there — but the authoritative event stream (snapshots) shows current_mana 70 at seq 896/897 while the sim final state ends at 75, indicating a mismatch in ordering/atomicity between emitted events and in-memory mutations during death handling.

## Files touched / inspected
- Instrumentation added (temporary): `src/waffen_tactics/services/combat_unit.py` (mana.setter printing old/new + stack)
- Investigated: `src/waffen_tactics/services/event_canonicalizer.py` (emit_mana_change, emit_mana_update, emit_unit_died)
- Investigated: `src/waffen_tactics/services/combat_attack_processor.py` (calls to `emit_mana_change` and scheduled attack logic)
- Logs: `/tmp/seed300_debug.txt`

## Evidence (high level)
- Event stream shows `mana_update` snapshot with `current_mana=70` (seq ~896/897).
- Instrumented writes show incremental mana increases up to 70, then a direct 70→75 write at the noted stack location.
- The direct write happened immediately after an `ENTER _process_unit_death killer=puszmen12 target=miki event_callback_set=True` log entry.

## Short diagnosis
- `emit_mana_change` mutates `recipient.mana` then emits `mana_update`. In death/attack scheduling there may be a race/ordering where a later in-memory mutation isn't matched by the event ordering/snapshot emission used by the reconstructor, causing the final reconstructor-applied state to differ.

## Actions taken
- Reproduced failing test deterministically.
- Instrumented `CombatUnit.mana` setter and re-ran test to capture stack trace of offending write.
- Located offending write and precise log context (file `/tmp/seed300_debug.txt`, line ~5549 in the saved run).

## Recommended next steps
1. Inspect the call site ordering in `CombatAttackProcessor.make_action` and `CombatSimulator.schedule_event` to ensure `emit_mana_change` is called with the same `timestamp` and that the emitted `mana_update` event arrives before any snapshot that the reconstructor will use. Consider making event emission atomic with HP/mana snapshot updates (update arrays and emit snapshot together).
2. Consider changing `emit_mana_change` to not mutate `recipient.mana` until after the event_callback has been invoked — OR ensure when mutating state it also updates the authoritative snapshot arrays used by the reconstructor at the same time (atomic update via `hp_arrays`-style pattern used for HP).
3. Remove temporary instrumentation from `combat_unit.py` once fixes are in place.

## Artifacts & locations
- Instrumented test output: `/tmp/seed300_debug.txt`
- Code:
  - `src/waffen_tactics/services/event_canonicalizer.py`
  - `src/waffen_tactics/services/combat_attack_processor.py`
  - `src/waffen_tactics/services/combat_unit.py` (instrumented)

## Quick commands used
```
pytest -q tests/test_combat_service.py -k seed_300 -s |& tee /tmp/seed300_debug.txt
grep -n "DEBUG MANA SET: unit=puszmen12 old=70 new=75" /tmp/seed300_debug.txt
sed -n '5538,5562p' /tmp/seed300_debug.txt
```

## Next / suggested options (choose one)
- A: I can implement the atomic snapshot + `emit_mana_change` ordering fix and run the failing test.
- B: I can remove the instrumentation and produce a cleaned commit/patch summarizing the fix options.
- C: You want a deeper trace: I can extract and paste the exact printed stack frames for the 70→75 write.

---
*If you'd like, I can proceed with option A and implement a minimal atomic update (patch `emit_mana_change` and any scheduling mismatch) and run the test.*
