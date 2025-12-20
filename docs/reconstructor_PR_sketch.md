PR sketch: Remove reconstructor synthetic repairs and require canonical backend events

Goal

- Remove all "synthetic repair" behavior from the reconstructor. The reconstructor must be a dumb applier of events and must fail loudly when snapshots disagree.
- Document the backend event schema changes required so the emitter provides the full lifecycle (apply/tick/expire) and authoritative numeric fields.

What changed in this PR

- Removed synthetic expiration injection and re-evaluation logic from `CombatEventReconstructor._compare_units`.
  - Rationale: reconstructor previously mutates reconstructed effects to "fix" mismatches. This masks missing events and allows nondeterministic replay.

Why backend changes are required

- The reconstructor previously computed deltas (percent → integer), derived DoT expiries when fields were missing, and injected synthetic expirations. Those are guesses and can diverge the replay.
- To make reconstruction deterministic, the backend emitter must provide canonical, self-contained events for:
  - effect_applied (generic) with `effect_id`, `applied_delta` or `applied_amount`, `expires_at`, and all necessary metadata
  - effect_expired with `effect_id`, `unit_id`, and authoritative `unit_hp`
  - damage_over_time_tick events that include `effect_id` and authoritative `unit_hp`
  - unit_update for authoritative top-level stat changes when they occur outside effects

Recommended canonical event schemas (examples)

- effect_applied

  {
    "seq": int,
    "timestamp": float,
    "unit_id": str,
    "effect_id": str,
    "type": "buff"|"debuff"|"shield"|"damage_over_time"|"stun",
    "stat": optional str,
    "value": optional number,
    "value_type": "flat"|"percentage",
    "applied_delta": optional int,
    "applied_amount": optional int,
    "amount": optional number,
    "damage": optional number,
    "interval": optional float,
    "ticks": optional int,
    "next_tick_time": optional float,
    "expires_at": optional float,
    "source": optional str
  }

- effect_expired

  {
    "seq": int,
    "timestamp": float,
    "unit_id": str,
    "effect_id": str,
    "unit_hp": optional int
  }

- damage_over_time_tick

  {
    "seq": int,
    "timestamp": float,
    "unit_id": str,
    "effect_id": str,
    "damage": int,
    "unit_hp": int
  }

- unit_update

  {
    "seq": int,
    "timestamp": float,
    "unit_id": str,
    "hp": int,
    "attack": optional int,
    "defense": optional int,
    ...
  }

Backport tasks (next steps)

1. Backend: emit `effect_applied` and `effect_expired` for every effect that appears in snapshots. Prefer emitting apply before the snapshot seq so reconstructor can replay deterministically.
2. Backend: always include `applied_delta`/`applied_amount` in apply events (compute server-side using engine rules and rounding).
3. Backend: standardize canonical keys (`effect_id`, `unit_hp`, `expires_at`, `ticks`, `interval`, `next_tick_time`).
4. Tests/CI: add a regression that fails CI if any snapshot contains effects which don't have prior `effect_applied` events within the event stream (or assert explicit snapshot-only semantics).
5. Remove other reconstructor heuristics once backend changes land (e.g., delta computation fallback, DoT expiry derivation).

Notes

- This PR intentionally makes the reconstructor stricter (fail-fast). The goal is to push correctness to the event emitter where it belongs.
- I can follow up with a small backend PR sketch that updates the emitter to the canonical schema and a CI test to guard snapshots.
