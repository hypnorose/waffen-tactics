# Waffen Tactics — Opponent Variety Audit

Generated: `2026-09-09`

## Executive summary

The seeded read-only audit completed **1** battles and observed **5** opponent units. It recorded **46** attacks, **0** skill casts, **15** passive events, and **0** observed position changes.

Unique behavior signatures: **5**. Repetition scan threshold: **3** occurrences. Runtime errors: **0**.

The report describes observed behavior and does not auto-edit units, traits, roles, or combat code.

## Classification counts

| Classification | Observations |
|---|---:|
| `repeated_basic_attack` | 5 |

## Required behavior dimensions

- Movement: position traces and movement-event counts are extracted from runtime snapshots. The controlled fixture uses front-line-first/back-line remainder placement; the current production opponent constructor still defaults every opponent to `front`.
- Target choice: every observed attack records target id and target position, plus distinct-target count.
- Action type: basic attacks and skill casts are counted separately. The current simulator skill hook is a no-op, so zero casts are explicit runtime evidence.
- Passive triggers: `passive_triggered`, `effect_applied`, and `effect_expired` are counted per opponent.
- Resource usage: mana event count, positive gain, negative spend/burn, and total delta are reported.
- Threat pattern: damage dealt, target distribution, survival, timeout, and winner are retained in JSON per battle/unit.

## Low-variety signatures

A repeated signature is a screening signal only. Defensive identity and the current basic-attack-only ruleset can legitimately produce repetition; no balance change is proposed automatically.

| Occurrences | Share | Classification | Identity-free signature |
|---:|---:|---|---|
| 0 | n/a | n/a | none |

## Opponent observations

| Seed | Unit | Role | Position | Attacks | Skills | Targets | Damage | Moved | Classification |
|---|---|---|---|---:|---:|---:|---:|---|---|
| `42000` | Dumb (`dumb`) | duelist | front | 11 | 0 | 1 | 484 | False | `repeated_basic_attack` |
| `42000` | Un4given (`un4given`) | defender | front | 6 | 0 | 1 | 144 | False | `repeated_basic_attack` |
| `42000` | Mrozu (`mrozu`) | fighter | front | 11 | 0 | 1 | 297 | False | `repeated_basic_attack` |
| `42000` | Adrianski (`adrianski`) | fighter | back | 5 | 0 | 1 | 215 | False | `repeated_basic_attack` |
| `42000` | Flaminga (`flaminga`) | fighter | back | 13 | 0 | 2 | 585 | False | `repeated_basic_attack` |

## Source and reproducibility

- Seed base: `42000`; matches: `1`; team size: `5`.
- Position contract: Controlled audit layout: front line first, back line remainder; movement is observed from runtime snapshots.
- Production position note: CombatManager currently constructs opponent units with position='front'; this audit does not silently treat that as movement or as a resolved positioning contract.
- Skill contract note: CombatSimulator._process_skill_cast is a no-op in the current ruleset; zero skill casts are reported as runtime evidence, not inferred missing actions.
- JSON artifact retains every seeded battle, raw per-unit observations, and errors for follow-up analysis.
