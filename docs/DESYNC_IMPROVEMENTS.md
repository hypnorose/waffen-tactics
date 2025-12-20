## DESYNC Improvements — Analysis & Fixes

Date: 2025-12-18

Purpose
- Summarize additional concrete fixes and improvements to make the game robust against DESYNCs (client shows different state than server).
- Prioritize actionable items, code-level changes, tests, runtime guards and operations playbook.

Executive summary
- Root cause: many event producers emit heterogeneous/legacy payloads and/or emit before the server in-memory state is mutated. Clients apply optimistic updates or incremental event patches but occasionally reconcile against snapshots that don't reflect recent events — causing visible DESYNCs.
- Primary mitigation already implemented: central `event_canonicalizer.py` and many emitters now perform best-effort in-memory mutation before returning canonical payloads. This reduces a large class of mismatches.
- Remaining surface area: snapshot sequencing, missing `seq`, legacy effect shapes, transient ordering windows, front-end reconciliation edge cases, telemetry/alerting gaps.

Top recommendations (short -> long term)

1) Add `seq` to all emitted events (short-term, high ROI)
- Rationale: timestamps aren't always monotonic or precise; `seq` gives total order and enables deterministic replay and easier reconciliation.
- Implementation:
  - Add an integer `seq_counter` on `CombatSimulator` (or central combat controller) that starts at 0 for each combat and increments for each emitted event.
  - Ensure `event_canonicalizer.emit_*` accepts an optional `seq` argument, or have the dispatcher attach `seq` as it sends events to SSE.
  - Include `seq` in both event JSON and any event logged to replay traces.

2) Make replay validator first-class test harness (short-term)
- Rationale: automated regression tests catch DESYNC regressions early.
- Implementation:
  - Add `tests/replay_validator.py` (or `waffen-tactics/tests/test_replay_validation.py`) that replays canonical JSONL traces using the canonical emitters to reconstruct state and compares against subsequent snapshots.
  - Normalize payload shapes in the validator (alias `amount` <-> `value`, `stat` -> `stats` list, `value_type`).
  - Fail CI when replay mismatch occurs.

3) Guarantee server in-memory mutation is authoritative (already done, extend to cover all producers)
- Rationale: events must reflect server state; emitting before mutation is a major cause of DESYNC.
- Implementation checklist:
  - Sweep all effect handlers and ensure they either call canonical emitters (preferred) or mutate state *and* return canonical payloads.
  - Add a linter/script that finds `event = ('...')` patterns that return non-canonical dicts and flag them for review.

4) Frontend reconciliation / robust store (short → medium)
- Rationale: client must deterministically apply events and gracefully reconcile snapshots.
- Improvements:
  - Use `seq` to order events and snapshots. Discard out-of-order events older than the latest snapshot seq.
  - Maintain `unitsById` canonical store on frontend; apply events deterministically (stateless pure reducers where possible).
  - On `state_snapshot` apply patch as authoritative for seq >= last snapshot seq; keep fields not provided in snapshot (e.g., `avatar/template_id`) if the frontend has them and they are semantically UI-only.
  - Implement `recomputeBuffedStats(unit)` that deterministically computes derived stats from `base_stats + effects` and compare with snapshot's `buffed_stats` (use tolerance for floats).
  - Add a grace window (e.g., 250–500ms) to avoid reporting transient small mismatches.

5) Event schema & contract tests (medium)
- Rationale: explicit contracts reduce accidental regressions.
- Actions:
  - Define canonical JSON schema (or pydantic dataclasses) for events (types: `stat_buff`, `heal`, `unit_heal`, `shield_applied`, `damage_over_time_tick`, `mana_update`, `mana_regen`, `unit_stunned`, `unit_died`, `state_snapshot`).
  - Add unit tests to assert event shapes (fields present / types / canonical aliases like `amount`).
  - Add a small runtime assertion wrapper in `event_canonicalizer` used in debug builds to validate event shapes before emission.

6) Idempotency & deduplication (medium)
- Rationale: network retries or duplicate processing can cause repeated application of the same effect.
- Implementation:
  - Include `event_id` (uuid) in emitted events — canonical emitter already generates effect ids for buffs; extend that to an event-level id in the dispatcher.
  - Replayers and frontend should ignore duplicate `event_id` / `seq` if already applied.

7) Snapshot improvements (medium)
- Rationale: snapshots are the authoritative reconciliation point; make them compact, include `seq`, and be consistent.
- Actions:
  - Always include `seq` in `state_snapshot` and ensure every snapshot corresponds to some last-seq event (or is an explicit authoritative snapshot with a new `seq`).
  - Snapshot must contain `effects` in canonical shape and `buffed_stats`. If computing `buffed_stats` is expensive server-side, compute incrementally or provide both raw `effects` and a `buffed_stats` cache.
  - Include `template_id`/`avatar` in snapshots to make UI resolution deterministic.

8) Telemetry & sampling (short → medium)
- Rationale: you need operational visibility into DESYNC frequency and types.
- Actions:
  - Add lightweight DESYNC report logging when the client detects a significant diff: a minimal payload { combat_id, seq, unit_id, diff_summary, client_version, timestamp }.
  - Sample reports (e.g., 1% or on first N per combat) to avoid high volume.
  - Integrate reports with Sentry/ELK or write to local file for initial rollouts.

9) Guardrails & invariants in code (short)
- Rationale: quick runtime checks prevent obvious corruption.
- Actions:
  - Add assertions in canonicalizers (only in debug builds) to assert invariants: hp <= max_hp, shield >= 0, durations >= 0.
  - Add defensive code in event dispatch path: if payload missing required fields, log error and attempt to canonicalize/repair rather than crash.

10) Contract migration plan & backcompat (ongoing)
- Rationale: the codebase contains many legacy emitter shapes; plan a safe migration.
- Steps:
  - Create an adapter layer near SSE/dispatcher that maps legacy shapes to canonical shapes (temporary compatibility layer).
  - Add deprecation logs for legacy emitters and a migration board (issues) to track replacement.

11) Tests & CI (must-have)
- Rationale: ensure regressions are caught early.
- Minimum tests to add:
  - `tests/test_replay_validation.py` — run the replay validator over a small set of canonical traces (`tests/traces/*.jsonl`).
  - `tests/test_event_schema.py` — assert event shapes and presence of `seq` and `event_id` in debug mode.
  - `tests/test_seq_monotonicity.py` — ensure emitted seqs are strictly increasing per combat.
  - `tests/test_idempotency.py` — replay traces with duplicate events and assert no double application.

12) Operational playbook (runbook)
- When a DESYNC report arrives:
  1. Check the `seq` and `combat_id` in the report and fetch the full trace from the server logs (the server should archive event JSONL for each combat when debugging is enabled).
  2. Run the replay validator against the trace locally to reproduce mismatch and create minimal repro.
  3. If reproducible, bisect recent code changes (or revert recent emitter changes) to identify the regression.

Appendix: recommended small code snippets

- Attaching `seq` near dispatcher (conceptual):

```py
# in CombatSimulator.__init__
self.seq_counter = 0

# when emitting
self.seq_counter += 1
payload = emit_stat_buff(...)
payload['seq'] = self.seq_counter
event_callback('stat_buff', {'type':'stat_buff','seq':self.seq_counter,'timestamp':ts,'data':payload})
```

- Replay validator: use canonical emitters to reapply events to an in-memory `ReplayUnit` model and compare to next `state_snapshot`.

Closing notes & priorities
- Immediate (days): add `seq`, add replay validator tests, continue sweeping any remaining legacy emitters and adapter layer.
- Short (1–2 weeks): finalize frontend `unitsById` authoritative store, implement idempotency, and add sampled telemetry.
- Medium (2–4 weeks): CI job for replay traces, monitoring dashboards and canary rollout with telemetry.

If you want, I can implement the first two items now:
1. Add `seq` attachment at the dispatcher (small patch across emitter call sites).
2. Add `tests/test_replay_validation.py` and a replay validator harness that uses canonical emitters.

Tell me which item to implement first and I'll create the patch and tests.
