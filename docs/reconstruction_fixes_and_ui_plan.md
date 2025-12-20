**Reconstruction Fixes & UI Update Plan**

- **Summary:** Reconstructor mismatches were caused by (1) the reconstructor inventing effects during expiry handling, (2) missing handling for `unit_stunned`, (3) brittle effect equivalence logic, and (4) mutable event payloads being stored by the test harness (simulator) which allowed later in-place mutations to change previously-emitted snapshots. I fixed the reconstructor and the event collection to make replay deterministic.

**Key fixes applied (files & rationale)**
- `waffen-tactics-web/backend/services/combat_event_reconstructor.py`:
  - Implemented `_process_stun_event` so `unit_stunned` events are reconstructed deterministically.
  - Removed spurious stun-appending in `effect_expired` (expiry should remove, not create effects).
  - Made snapshot expiry filtering robust to `expires_at = None` (treat None as "no expiry").
  - Improved stat buff equivalence to compare `value`/`amount`/`applied_delta` canonical numeric values.
  - Pruned reconstructed effects absent from authoritative snapshots (snapshot is ground-truth).
- `waffen-tactics-web/backend/services/combat_service.py`:
  - Deep-copy event payloads when collecting emitted events to prevent later in-place simulator mutations from changing stored snapshots.

**Why these broke determinism**
- The reconstructor previously could both fail to recreate legitimately emitted stuns and also create effects during an `effect_expired` handler. That produces divergence vs snapshots.
- More subtly, storing references to mutable payload dicts allowed the simulator to mutate unit objects (e.g. `unit.effects`) after the collector appended the payload; the collected snapshot no longer reflected the emitter's authoritative payload at emission time. Deep-copying fixes that class of bugs.

**Exact invariants enforced by fixes**
- Every effect applied by an "apply" event must later be removed by an explicit expire event (matching `effect_id`) or be present in snapshot payloads.
- Collected event payloads are immutable copies of the emitter's authoritative payload at emission time.

**UI update plan (concise)**
1. Data contract: Ensure UI reads and displays these fields from snapshot/effect objects: `id`, `type`, `stat`, `value`, `value_type`, `applied_delta`, `source`, `expires_at`.
2. Effect tooltip: Show `value` (and `applied_delta` when present) and `source` + remaining time computed from `expires_at`.
3. Missing fields: If `applied_delta` is absent for a stat buff, UI should compute display value from `value`/`amount` and `value_type` but mark it as "derived" in the tooltip.
4. Expiry visuals: Treat `expires_at == null` as persistent; show a persistent icon instead of a countdown.
5. Re-rendering: When receiving a `state_snapshot`, replace unit effect lists wholesale (authoritative). Avoid incremental patching based on previous client state for deterministic display.
6. Tests & QA: Add an integration test that replays a recorded event stream and asserts the UI (or minimal frontend state model) matches the final snapshot.

**Suggested implementation steps for UI team**
- Update frontend model to accept `applied_delta` and `effect.id` fields.
- Update effect list rendering and tooltip to include `source` and `applied_delta` (fallback to derived).
- Add handling for `expires_at === null` as persistent effects.
- Add integration test harness that replays saved event streams (use the same emitted JSON format) and asserts UI model equals snapshot data.

File created by developer action during debugging: `docs/reconstruction_fixes_and_ui_plan.md`
