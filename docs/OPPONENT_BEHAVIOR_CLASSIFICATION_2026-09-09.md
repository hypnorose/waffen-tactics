# Opponent Behavior Classification

Generated: `2026-09-09`

This report classifies opponent behavior without treating an absent action as a
bug by default. It is a read-only companion to
`docs/OPPONENT_VARIETY_AUDIT_2026-09-09.md`.

## Observed seeded runtime behavior

- 50 battles and 250 opponent observations completed with 0 runtime errors.
- All 250 observations were `repeated_basic_attack`.
- The run emitted 0 skill casts and recorded 0 position changes.
- The controlled audit layout observed front-line-first/back-line-remainder;
  `CombatManager` still constructs production opponents with `position='front'`.

## Classification contract

| Category | Evidence required | Seeded test case |
|---|---|---|
| `intentional_defensive_identity` | Authored defensive identity or other explicit behavior explains the hold | `157004` |
| `no_legal_action` | Unit remains alive but the opposing team has no live legal target | `157005` |
| `repeated_basic_attack` | At least two basic attacks and no skill cast | `157001` |
| `missing_position_rule` | Position is normalized/defaulted instead of coming from an explicit contract | `157007` |
| `runtime_defect_candidate` | Unit remains eligible and alive without an emitted action | `157006` |
| `combat_ended_before_action` | Unit dies before an attack event is emitted | `157003` |

The classifier test covers the observable categories. The seeded production run
only observed repeated basic attacks, so the other categories are not claimed as
live opponent outcomes. The position-rule finding is a setup/ownership gap,
not an inferred movement behavior.

## Follow-up boundary

The existing `DEF-178` issue is the runtime follow-up for validating supported
position values and consolidating the position owner. `DEF-154` remains the
manual-only owner for approving the front/back targeting contract. No dataset or
opponent behavior was changed by this audit.
