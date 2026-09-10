# Seeded Scenario Matrix

Generated: `2026-09-09`

This is a read-only, deterministic matrix for the current runtime contract. It
does not add units, traits, or permanent content. The `seed` values identify
stable scenario identities; the executable expectations live in the referenced
tests and audit runner.

| Scenario | Seed | Formation | Expected pattern | Runner |
|---|---:|---|---|---|
| Frontline then backline | 158001 | A front / B front+back | Front target, then back after death | `test_approved_combat_rules.py` |
| No legal target no-op | 158002 | A front / B front | No attack; stale focus cleared | `test_approved_combat_rules.py` |
| Team A before Team B | 158003 | A front / B front | Same-tick A attack precedes B attack | `test_approved_combat_rules.py` |
| Full tempo bonus attack | 158004 | A front / B front | One bonus basic attack; no skill cast | `test_approved_combat_rules.py` |
| Enemy death trigger | 158005 | A front / B front | Death emits stat rewards | `test_combat_shared.py` |
| Ally death trigger once | 158006 | A front / B front+back | One gold reward for one death | `test_combat_shared.py` |
| Low-HP threshold | 158007 | A front+back / B front | Authoritative threshold trigger | `test_combat_effect_processor.py` |
| Trait threshold control | 158008 | A front / B front | Below/exact/next tier states | `tools/balance_audit.py` |
| Canonical replay parity | 158009 | A front+back / B front+back | Zero snapshot desyncs | `approved_replay_golden.json` |

## Reproducibility contract

- Seeds and expected patterns are versioned in the JSON matrix.
- The matrix validator rejects duplicate or missing seeds, incomplete formation
  metadata, missing acceptance notes, and missing runner references.
- The core, backend, and frontend replay tests consume the same
  `approved_replay_golden.json` fixture for the cross-layer parity row.
- A scenario failure is classified by the owning runner: data, runtime,
  emitter, reconstructor, UI, or audit tooling.
