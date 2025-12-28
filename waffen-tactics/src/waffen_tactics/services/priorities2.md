Concrete components to refactor (priority order)

Event system: split event_canonicalizer into

payload_builders (pure functions that take domain state & produce canonical payloads)
state_mutators (single responsibility functions that apply a payload to domain state)
EventDispatcher that composes builders+mutators and handles seq/timestamps, idempotency, and callback delivery.
Files: split event_canonicalizer.py → emitters/payload.py, emitters/mutators.py, emitters/dispatcher.py
Benefits: test payload builders without side-effects; easier reconstructor correctness.
Domain models: extract typed dataclasses for domain objects

CombatUnit → make a small immutable/mostly-plain dataclass + mutable runtime wrapper for combat state (hp, shield, mana).
Introduce Stats, Skill, Effect types (dataclasses/TypedDicts).
File: refactor combat_unit.py into models/unit.py, models/stats.py, models/effect.py.
Benefits: clearer type contracts, easier property-based tests, deterministic serialization.
Clear authoritative state model: pick single source of truth for HP/mana (prefer unit instance), remove a_hp/b_hp lists or encapsulate them in a CombatState object that is synchronized explicitly.

Create CombatState that stores lists of UnitWrappers and exposes get_snapshot() and deterministic apply/rollback methods.
Update combat_simulator.py to use CombatState.
Benefits: remove ad-hoc sync code in _emit_state_snapshot, avoid duplication/desync.
Simulation core vs processors separation:

Turn processors (attack/regen/effects/per-second) into pure-ish services with signature like:
AttackProcessor.compute_attacks(state: CombatState, time: float) -> List[EventPayload]
AttackProcessor.apply(events, state, dispatcher) where apply uses dispatcher to apply changes.
This decouples decision logic (deterministic) from mutation+emission.
Files: refactor combat_attack_processor.py, combat_effect_processor.py, etc.
Event reconstructor (consumer): ensure it only consumes events and never relies on in-memory state mutations; split any code that mixes reconstruction with API helpers.

If present in top-level services/combat_event_reconstructor.py or other, make it strict-read-only.
Suggested new file structure (incremental)

waffen-tactics/src/waffen_tactics/models/
unit.py (dataclass/typed)
stats.py
skill.py
effect.py
waffen-tactics/src/waffen_tactics/engine/
combat_state.py (single authoritative state)
sim_loop.py (SimulationLoop orchestrator — timing, tick)
event_dispatcher.py (wraps callbacks, seq, idempotency)
waffen-tactics/src/waffen_tactics/processors/
attack.py (pure compute + small apply wrapper)
regen.py
per_second_buffs.py
effect_handlers.py
waffen-tactics/src/waffen_tactics/emitters/
payload.py (pure payload builders)
mutators.py (apply payloads to state)
canonical.py (thin facade calling payload+mutator)
Keep tests under tests/ mirroring the above.
Minimal incremental refactors (quick wins)

Replace CombatUnit init duplication and remove _set_mana(caller_module) guard; expose set_mana(new) and restrict callers in code review (or accept a mutator object). This is a small change with immediate clarity.
File: combat_unit.py
Extract EventDispatcher from _create_event_callback_wrapper into engine/event_dispatcher.py — keep behavior but centralize. Then CombatSimulator uses the dispatcher.
File: combat_simulator.py
Add CombatState wrapper around the a_hp/b_hp sync logic and change _emit_state_snapshot to call CombatState.get_snapshot().
Testing & correctness suggestions

Add unit tests for:
Pure payload builders in new emitters/payload.py (no side-effects).
Attack damage calculation in processors/attack.py using property-based tests (random stats within bounds).
Snapshot deterministic invariants: run simulation with deterministic targeting and assert that applying the sequence of emitted events reconstructs final state exactly.
Add contract tests for EventDispatcher: dropped callback must not advance seq; event payload normalization must not mutate original payload object.
Add invariants to assert during simulation: after each tick assert unit.hp == combat_state.hp_list (during transitional refactor use assertions to find desyncs).
Next 2–3 recommended tasks (small, ordered)

Create engine/event_dispatcher.py by extracting _create_event_callback_wrapper behavior and replace usage in CombatSimulator. (Low risk, centralizes complexity.)
Introduce models/ dataclass for CombatUnit (or a UnitState wrapper), and add a set_mana public method — remove _set_mana permission string check. Update callers in emitters to use new method. (Medium risk, unit-local)
Add engine/combat_state.py to encapsulate HP lists and snapshot creation; update _emit_state_snapshot to call it. (Medium risk, eliminates ad-hoc sync spots.)

## Scan notes (automated additions)

- Short findings:
	- `CombatSimulator` duplicates state (per-unit fields vs `a_hp`/`b_hp`) leading to desync risk.
	- `event_canonicalizer.py` mixes payload building and state mutation; split builders/mutators.
	- Dispatcher wrapping is used in multiple places; centralize into `engine/event_dispatcher.py` and inject the dispatcher instance into processors.

- Tests: ensure reconstructor only consumes canonical `unit_attack` events; legacy `attack` checks have been removed from core tests.

Suggested immediate actions:
- Add `TODO: REFACTOR` comments at top of `event_canonicalizer.py`, `combat_simulator.py`, and `combat_attack_processor.py`.
- Implement `engine/event_dispatcher.py` next (low-risk, high-benefit).