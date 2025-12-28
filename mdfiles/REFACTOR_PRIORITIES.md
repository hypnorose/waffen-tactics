./# Refactor Priorities — Waffen Tactics

Date: 2025-12-23 (Updated: 2025-12-24)

This document captures the refactor recommendations, priorities, rationale, and next steps gathered from a quick code review of the repository (core combat modules). Use this as a living checklist for incremental improvements.

## Project context
- Core files inspected: `waffen-tactics/src/waffen_tactics/services/combat_simulator.py`, `combat_unit.py`, `combat_attack_processor.py`, `event_canonicalizer.py`.
- Gameplay assumptions: tick-based simulation (dt=0.1s), teams of `CombatUnit`s, attack-speed-driven attacks, mana-driven skills, and an event emission pipeline for authoritative replay.

## High-risk coupling / anti-patterns
- Monolithic `CombatSimulator` mixing orchestration, state tracking, and event sequencing.
- Dual authoritative state: per-unit fields (`unit.hp`, `unit.mana`) vs separate HP lists (`a_hp`, `b_hp`) with ad-hoc sync.
- Emitters mutate domain state *and* produce payloads; hard to test payloads independently.
- `CombatUnit` initializer contains duplication and a guard `_set_mana(caller_module)` that makes testing and callers brittle.
- Processors (attack/regen/effects) interleave decision logic with direct state mutation and event emission.

## Refactor components (priority order)

1) Event system (High priority)
   - Goal: separate payload construction from state mutation and delivery.
   - Actions: split `event_canonicalizer.py` into
     - `emitters/payload.py` (pure payload builders),
     - `emitters/mutators.py` (state-changing helpers),
     - `engine/event_dispatcher.py` (wraps callbacks, seq/timestamps/idempotency).
   - Rationale: Easier unit tests for payloads, deterministic replays, clearer idempotency.

2) Domain models (High priority) ✅ COMPLETED
   - Goal: introduce typed dataclasses for `Stats`, `Skill`, `Effect`, and a clearer `UnitState` wrapper.
   - Actions: create `models/unit.py`, `models/stats.py`, `models/skill.py`; reduce mutations in constructor; remove `_set_mana(caller_module)`.
   - Rationale: clearer type contracts and easier property-based testing.
   - Status: ✅ Implemented CombatUnitStats/CombatUnitState dataclasses, property-based API with immutable stats and mutable state separation, comprehensive property accessors with setters for effects compatibility. All combat tests passing.

3) Authoritative CombatState (Medium priority)
   - Goal: single source of truth for HP/mana during simulation.
   - Actions: add `engine/combat_state.py` encapsulating teams, hp lists, snapshot generation and synchronization routines.
   - Rationale: eliminate ad-hoc sync logic in `_emit_state_snapshot` and reduce desync risk.

4) Separate compute vs apply in processors (Medium priority)
   - Goal: split processors into `compute` (pure) and `apply` (mutating + emitting) phases.
   - Actions: refactor `combat_attack_processor.py`, `combat_effect_processor.py` into `processors/attack.py`, `processors/effects.py` with `compute_*` functions returning events.
   - Rationale: easier to test deterministic decision logic and to replay/apply events safely.

5) Reconstructor & Test harness (Low/Medium priority)
   - Goal: make reconstructor consumer-only and add contract tests proving replay determinism.
   - Actions: ensure `combat_event_reconstructor.py` consumes canonical events only and add tests that apply events to `CombatState` to reproduce final states.

## Minimal incremental tasks (recommended order)
1. Extract `EventDispatcher`: move `_create_event_callback_wrapper` logic into `engine/event_dispatcher.py` and replace usage in `combat_simulator.py`. (Low risk)
2. Add `models/unit.py`: small typed dataclass or wrapper exposing `set_mana`, `take_damage`, `heal`. Remove caller-string guard. Update emitters to call these public methods. (Medium risk)
3. Create `engine/combat_state.py` to encapsulate `a_hp`/`b_hp` logic and snapshot API; update `_emit_state_snapshot` to use it. (Medium risk)
4. Refactor `combat_attack_processor` to compute events first, then apply via dispatcher. (Higher effort)

## Tests & invariants to add
- Unit tests for payload builders (pure inputs → canonical payloads).
- Property-based tests for damage calculation invariants (damage >= 1, monotonic hp decrease on damage-only events).
- Replay contract test: run simulation with deterministic targeting and assert replaying emitted events reconstructs final `CombatState`.
- Invariant assertions during simulation (temporary): assert `unit.hp == combat_state.hp_list[index]` after each emitter application.

## Files to change (first-pass)
- `waffen-tactics/src/waffen_tactics/services/event_canonicalizer.py` → split into `emitters/` and `engine/event_dispatcher.py`.
- `waffen-tactics/src/waffen_tactics/services/combat_unit.py` → `models/unit.py` and simplify API.
- `waffen-tactics/src/waffen_tactics/services/combat_simulator.py` → use `engine/event_dispatcher.py` and `engine/combat_state.py`.
- `waffen-tactics/src/waffen_tactics/services/combat_attack_processor.py` → `processors/attack.py` with compute/apply separation.

## Next actions (pick one)
- A. Implement `engine/event_dispatcher.py` and update `combat_simulator.py` to use it. (Fast, recommended first step - now priority 1)
- B. Create `engine/combat_state.py` and replace ad-hoc hp sync. (Medium effort - now priority 2)
- C. Refactor `combat_attack_processor` to compute events first, then apply via dispatcher. (Higher effort - now priority 3)

If you'd like, I can implement option A now with a small patch and tests. Reply with your choice and I'll proceed.

---
Generated by Copilot during initial repo review. Keep this file updated as the refactor work progresses.
