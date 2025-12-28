# Stack Mapping Report — seed 300

Summary
- Purpose: map saved stack trace from `notes/stack-puszmen12-70-75.txt` to repository sources and capture surrounding code to explain root cause.
- Outcome: created this report and committed to repo (see commit message below).

Mapped frames

- Test harness
  - File: [waffen-tactics-web/backend/tests/test_combat_service.py](waffen-tactics-web/backend/tests/test_combat_service.py#L778)
  - Context: calls `self._test_single_seed_simulation(300)` which runs the seeded simulation.

- Test helper
  - File: [waffen-tactics-web/backend/tests/test_combat_service.py](waffen-tactics-web/backend/tests/test_combat_service.py#L835)
  - Context: `_test_single_seed_simulation` invokes `run_combat_simulation(player_units, opponent_units)`.

- Backend service caller
  - File: [waffen-tactics-web/backend/services/combat_service.py](waffen-tactics-web/backend/services/combat_service.py#L581)
  - Context: collects events then calls `simulator.simulate(player_units, opponent_units, event_collector)`.

- Simulator loop
  - File: [src/waffen_tactics/services/combat_simulator.py](src/waffen_tactics/services/combat_simulator.py#L496)
  - Context: `simulate()` orchestrates the timestep loop and calls `_process_team_attacks(...)`.

- Attack processor (mana emission)
  - File: [src/waffen_tactics/services/combat_attack_processor.py](src/waffen_tactics/services/combat_attack_processor.py#L216)
  - Context (excerpt):

```
combat_state = getattr(self, '_combat_state', None)
if combat_state is not None:
    emit_mana_change(event_callback, unit, amount, side=side, timestamp=attack_ts, mana_arrays=combat_state.mana_arrays, unit_index=i, unit_side=side)
else:
    emit_mana_change(event_callback, unit, amount, side=side, timestamp=attack_ts)
```

- Event canonicalizer (where unit state is mutated)
  - File: [src/waffen_tactics/services/event_canonicalizer.py](src/waffen_tactics/services/event_canonicalizer.py#L294)
  - Context (excerpt):

```
if mana_arrays and unit_index is not None and unit_side:
    if unit_side in mana_arrays and 0 <= unit_index < len(mana_arrays[unit_side]):
        mana_arrays[unit_side][unit_index] = new_val

if hasattr(recipient, '_set_mana'):
    recipient._set_mana(new_val, caller_module='event_canonicalizer')
else:
    recipient.mana = new_val
```

- Unit setter (instrumented during debug)
  - File: [src/waffen_tactics/services/combat_unit.py](src/waffen_tactics/services/combat_unit.py#L128)
  - Context: `mana` property setter — previously printed stack traces; now quiet after cleanup.

Root cause summary
- The stack shows `emit_mana_change` performing the write that produced the `DEBUG MANA SET` trace. Historically, mana was mutated at unit-level without an authoritative mirror used for snapshots; snapshots and unit-local writes could be emitted in different orders, producing reconstructor desyncs.
- The implemented mitigation centralizes authoritative mana into `CombatState.mana_arrays`, updates them atomically in `emit_mana_change`, and uses `_set_mana` to mutate unit state in a controlled fashion. Temporary debug prints in `CombatUnit.mana` were removed.

Suggested commit message (used)

Title: Make mana authoritative in CombatState; atomically update emitter and remove debug logging

Body:
- Add `mana_arrays` to `CombatState` and sync plumbing for snapshots.
- Update `emit_mana_change` to accept `mana_arrays` and update them atomically.
- Update processors/callers to pass `combat_state.mana_arrays`.
- Remove temporary debug prints from `CombatUnit.mana`.

Notes
- If you want a PR opened, I can create a branch and open a PR with this report attached.


