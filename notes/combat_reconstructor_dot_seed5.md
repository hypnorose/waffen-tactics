Summary: Reconstructor DoT trace (seed=5)

Key facts
- Unit: mrvlook
- Seed: 5
- DoT applied canonical event: seq=52, effect_id=259b8230-e402-4c1f-939f-1751629346ad, damage=20, unit_hp=600, timestamp≈43.2
- Reconstructor: appended applied entry for seq=52 (unit_hp=600), then injected synthetic_expire at seq=53
- Canonical snapshot: seq=329 shows mrvlook hp=520 and contains damage_over_time id=10c41d34-... ticks_remaining=2 (next_tick_time≈58.0)
- Canonical snapshot: seq=397 shows mrvlook hp=464 and damage_over_time ticks_remaining=1 (next_tick_time≈60.0)

Observed symptom
- Reconstructor final hp for mrvlook is 444 (−20) lower than authoritative snapshot (464).

Preliminary diagnosis
- Server emits DoT as effect entries embedded in snapshots but does not emit explicit per-tick authoritative "tick" events with effect_id + authoritative unit_hp.
- Reconstructor infers tick lifecycle and injects synthetic expirations; missing explicit tick/expire messages allows subtle off-by-one/missed tick cases.

Recommended minimal server-side fix
- Emit explicit DoT tick events when a tick applies, and explicit effect_expire events on expiration.
  - `damage_over_time_tick` fields: seq, timestamp, effect_id, unit_id, damage, authoritative_unit_hp
  - `damage_over_time_expire` fields: seq, timestamp, effect_id, unit_id
- This keeps the reconstructor minimal: it should consume authoritative tick/expire events rather than inferring lifecycle from snapshots.

Next steps
1. Extract canonical events in seq windows ~45–60 and ~325–335 and align with reconstructor `_dot_trace` entries.
2. Confirm whether any duplicate/misordered ticks are emitted or only missing tick events cause the desync.
3. If confirmed, implement the server-side emission of `damage_over_time_tick` / `damage_over_time_expire` (small patch to canonicalizer/event emitter).

Logs & artifacts
- Log used: /tmp/pytest_seed5_run3.txt
- Reconstructor instrumented file: waffen-tactics-web/backend/services/combat_event_reconstructor.py

Saved on: 2025-12-20
