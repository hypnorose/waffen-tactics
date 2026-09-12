# Waffen Tactics — Balance Audit

Generated: `2026-09-12`

## Executive summary

Runtime data contains **32 units** and **12 traits**. The audit ran **100 team battles** (100 each for 3v3) and **890 controlled same-cost pairwise simulations**.

Unit status counts: underpowered **13**, healthy **8**, overpowered **11**, insufficient data **0**.

The status is a screening signal, not an automatic balance patch. Pairwise data is primary; random-team data is reported separately because traits, composition, target selection, and side asymmetry confound it.

## Findings and disposition

- Must-fix: `0`.
- Should-fix: `1`.
- Accepted risks: `2`.

Each finding records its baseline, proposed change, and expected consequence. No numeric unit, trait, or economy value is changed by this audit.

### Must-fix

### Should-fix

- `balance.unit_screening_outliers` (unit values and passives): Author-review the per-unit baseline/proposed actions in unit_statuses; do not apply automatic numeric changes. Baseline: `{'underpowered': 13, 'healthy': 8, 'overpowered': 11, 'outlier_units': ['4tune', '9wojtaz9', 'alyson_stark', 'anamol04', 'aus_sher', 'bbobel', 'chessowy_mentos', 'empty_melancholy', 'fiko', 'galanonim', 'jadlainwestycji', 'jaeger', 'klemens_zydoslawski', 'knauff', 'kotmarcek', 'marcel_galadotka', 'merex', 'mr0czeq1', 'pytl', 'skibidi_kubus', 'sofronow', 'szachowymentor', 'szalwia', 'yossarian']}` Consequence: Unit changes are reviewed after system-rule findings, avoiding a unit patch that masks a systemic imbalance.
### Accepted risks

- `metadata.legacy_faction_class` (historical faction/class metadata): No active Set 2 change; retain as non-blocking legacy metadata until an author explicitly normalizes it. Baseline: `[{'unit_id': 'skibidi_kubus', 'missing': ['classes']}]` Consequence: The active runtime remains on the approved 32-unit/12-trait contract without invented mappings.
- `measurement.pairwise_screen` (balance interpretation): Keep the raw JSON and seeds; repeat after any approved rules or value change. Baseline: `Controlled same-cost pairwise is primary, while team context is confounded by traits, composition, target selection, and side asymmetry.` Consequence: The report remains evidence for author review rather than an automatic balancing authority.

## Acceptance criteria

- Team battles: `100/100`; simulator errors: `0`; timeouts: `0`.
- Controlled pairwise errors: `0`; timeouts: `0`.
- Controlled trait threshold errors: `0`; threshold rows: `32`.
- Same-seed determinism probe: **PASS**.
- No game data or gameplay code is changed by this audit.

## Roster integrity

- Cost distribution: `{1: 6, 2: 7, 3: 8, 4: 6, 5: 5}`.
- Role distribution: `{'defender': 7, 'duelist': 11, 'fighter': 6, 'mage': 8}`.
- Duplicate unit IDs: `none`.
- Missing required fields: `none`.
- Invalid costs/roles: `none` / `none`.
- Active Set 2 contract issues: `none`.
- Legacy faction/class metadata gaps (non-blocking): `[{'unit_id': 'skibidi_kubus', 'missing': ['classes']}]`.
- Trait schema issues: `none`.
- Skill effect types: `{'damage': 32}`.

## Unit verdicts

Thresholds: pairwise win rate ≤35% = underpowered, ≥65% = overpowered; otherwise healthy. These cutoffs are intentionally conservative screening thresholds. Numeric value changes are not applied.

| Unit | Cost | Role | Pairwise | Team context | Sample | Status | Next action |
|---|---:|---|---:|---:|---:|---|---|
| 4tune | 4 | duelist | 90.0% | 62.5% | 50 | **overpowered** | review for a nerf after system rules are normalized |
| 9wojtaz9 | 1 | duelist | 80.0% | 34.8% | 50 | **overpowered** | review for a nerf after system rules are normalized |
| alyson_stark | 4 | duelist | 90.0% | 75.0% | 50 | **overpowered** | review for a nerf after system rules are normalized |
| anamol04 | 2 | fighter | 83.3% | 52.9% | 60 | **overpowered** | review for a nerf after system rules are normalized |
| aus_sher | 3 | mage | 28.6% | 35.7% | 70 | **underpowered** | review for a buff after system rules are normalized |
| bbobel | 1 | defender | 30.0% | 44.0% | 50 | **underpowered** | review for a buff after system rules are normalized |
| boczek | 1 | defender | 60.0% | 27.3% | 50 | **healthy** | keep values and monitor after system-rule fixes |
| chessowy_mentos | 2 | mage | 16.7% | 38.1% | 60 | **underpowered** | review for a buff after system rules are normalized |
| empty_melancholy | 3 | defender | 14.3% | 31.6% | 70 | **underpowered** | review for a buff after system rules are normalized |
| fallensmokk | 2 | fighter | 58.3% | 47.6% | 60 | **healthy** | keep values and monitor after system-rule fixes |
| fiko | 5 | duelist | 75.0% | 78.3% | 40 | **overpowered** | review for a nerf after system rules are normalized |
| galanonim | 5 | fighter | 25.0% | 56.2% | 40 | **underpowered** | review for a buff after system rules are normalized |
| jadlainwestycji | 3 | duelist | 78.6% | 56.2% | 70 | **overpowered** | review for a nerf after system rules are normalized |
| jaeger | 1 | defender | 20.0% | 40.9% | 50 | **underpowered** | review for a buff after system rules are normalized |
| kaktusek | 2 | fighter | 58.3% | 50.0% | 60 | **healthy** | keep values and monitor after system-rule fixes |
| klemens_zydoslawski | 4 | mage | 0.0% | 47.1% | 50 | **underpowered** | review for a buff after system rules are normalized |
| knauff | 3 | duelist | 100.0% | 58.8% | 70 | **overpowered** | review for a nerf after system rules are normalized |
| kotmarcek | 2 | duelist | 100.0% | 55.0% | 60 | **overpowered** | review for a nerf after system rules are normalized |
| marcel_galadotka | 2 | mage | 0.0% | 25.0% | 60 | **underpowered** | review for a buff after system rules are normalized |
| merex | 5 | duelist | 100.0% | 100.0% | 40 | **overpowered** | review for a nerf after system rules are normalized |
| mr0czeq1 | 2 | mage | 33.3% | 35.3% | 60 | **underpowered** | review for a buff after system rules are normalized |
| nicosc | 4 | defender | 60.0% | 41.2% | 50 | **healthy** | keep values and monitor after system-rule fixes |
| optimusprime | 3 | fighter | 50.0% | 56.2% | 70 | **healthy** | keep values and monitor after system-rule fixes |
| pytl | 4 | mage | 20.0% | 46.7% | 50 | **underpowered** | review for a buff after system rules are normalized |
| skibidi_kubus | 1 | duelist | 100.0% | 50.0% | 50 | **overpowered** | review for a nerf after system rules are normalized |
| sofronow | 1 | defender | 10.0% | 31.2% | 50 | **underpowered** | review for a buff after system rules are normalized |
| szachowymentor | 5 | mage | 0.0% | 50.0% | 40 | **underpowered** | review for a buff after system rules are normalized |
| szalwia | 3 | mage | 0.0% | 30.8% | 70 | **underpowered** | review for a buff after system rules are normalized |
| szanowny_kantor | 4 | defender | 40.0% | 55.6% | 50 | **healthy** | keep values and monitor after system-rule fixes |
| uhla | 3 | fighter | 50.0% | 50.0% | 70 | **healthy** | keep values and monitor after system-rule fixes |
| vitas | 5 | duelist | 50.0% | 80.0% | 40 | **healthy** | keep values and monitor after system-rule fixes |
| yossarian | 3 | duelist | 78.6% | 59.1% | 70 | **overpowered** | review for a nerf after system rules are normalized |

## Role and cost results

| Group | Appearances | Wins | Win rate |
|---|---:|---:|---:|
| role: defender | 139 | 54 | 38.8% |
| role: duelist | 208 | 133 | 63.9% |
| role: fighter | 116 | 60 | 51.7% |
| role: mage | 137 | 53 | 38.7% |
| cost: 1 | 124 | 47 | 37.9% |
| cost: 2 | 140 | 61 | 43.6% |
| cost: 3 | 139 | 67 | 48.2% |
| cost: 4 | 107 | 60 | 56.1% |
| cost: 5 | 90 | 65 | 72.2% |

## Trait thresholds — controlled tests

Every authored threshold is listed. The trait team is compared with a same-size control team in both orientations. A tier with no valid controlled observations is `insufficient data`; these results must not drive a unit nerf/buff before system rules are normalized.

| Trait | Tier | Threshold | Decisive battles | Trait wins | Trait WR | Control WR | Delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| Konfident | 1 | 3 | 10 | 0 | 0.0% | 100.0% | -100.0% |
| Konfident | 2 | 5 | 10 | 0 | 0.0% | 100.0% | -100.0% |
| Konfident | 3 | 7 | 10 | 0 | 0.0% | 100.0% | -100.0% |
| Wierny widz | 1 | 3 | 10 | 7 | 70.0% | 30.0% | 40.0% |
| Wierny widz | 2 | 5 | 10 | 6 | 60.0% | 40.0% | 20.0% |
| Wierny widz | 3 | 6 | 10 | 4 | 40.0% | 60.0% | -20.0% |
| Nowociota | 1 | 3 | 10 | 1 | 10.0% | 90.0% | -80.0% |
| Nowociota | 2 | 5 | 10 | 0 | 0.0% | 100.0% | -100.0% |
| Nowociota | 3 | 7 | 10 | 0 | 0.0% | 100.0% | -100.0% |
| Figlarz | 1 | 2 | 10 | 10 | 100.0% | 0.0% | 100.0% |
| Figlarz | 2 | 4 | 10 | 8 | 80.0% | 20.0% | 60.0% |
| Figlarz | 3 | 6 | 10 | 7 | 70.0% | 30.0% | 40.0% |
| Weeb | 1 | 2 | 10 | 8 | 80.0% | 20.0% | 60.0% |
| Weeb | 2 | 4 | 10 | 7 | 70.0% | 30.0% | 40.0% |
| Weeb | 3 | 6 | 10 | 4 | 40.0% | 60.0% | -20.0% |
| Starociota | 1 | 2 | 10 | 10 | 100.0% | 0.0% | 100.0% |
| Starociota | 2 | 3 | 10 | 9 | 90.0% | 10.0% | 80.0% |
| Starociota | 3 | 5 | 10 | 10 | 100.0% | 0.0% | 100.0% |
| Inwestor | 1 | 2 | 10 | 8 | 80.0% | 20.0% | 60.0% |
| Inwestor | 2 | 3 | 10 | 10 | 100.0% | 0.0% | 100.0% |
| Inwestor | 3 | 4 | 10 | 10 | 100.0% | 0.0% | 100.0% |
| Femboy | 1 | 2 | 10 | 9 | 90.0% | 10.0% | 80.0% |
| Femboy | 2 | 3 | 10 | 9 | 90.0% | 10.0% | 80.0% |
| Femboy | 3 | 5 | 10 | 7 | 70.0% | 30.0% | 40.0% |
| Szachista | 1 | 2 | 10 | 2 | 20.0% | 80.0% | -60.0% |
| Szachista | 2 | 3 | 10 | 4 | 40.0% | 60.0% | -20.0% |
| Twórca | 1 | 2 | 10 | 3 | 30.0% | 70.0% | -40.0% |
| Twórca | 2 | 3 | 10 | 6 | 60.0% | 40.0% | 20.0% |
| Muzyk | 1 | 1 | 10 | 2 | 20.0% | 80.0% | -60.0% |
| Muzyk | 2 | 2 | 10 | 1 | 10.0% | 90.0% | -80.0% |
| Haxball | 1 | 2 | 10 | 6 | 60.0% | 40.0% | 20.0% |
| Haxball | 2 | 3 | 10 | 8 | 80.0% | 20.0% | 60.0% |

## Stat budget and star scaling

The runtime currently scales HP by ×1.6 and attack by ×1.4 per star step; defense, attack speed, and max mana remain at base values. See the JSON artifact for every role/cost row and 1★/2★/3★ values.

| Role | Cost | Representative | HP | Attack | Defense | Speed | DPS | Max mana | Mana/attack | Regen |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| defender | 1 | sofronow | 600 | 30 | 30 | 0.80 | 24.00 | 100 | 4 | 4 |
| defender | 3 | empty_melancholy | 840 | 42 | 42 | 0.80 | 33.60 | 100 | 4 | 4 |
| defender | 4 | szanowny_kantor | 960 | 48 | 48 | 0.80 | 38.40 | 100 | 4 | 4 |
| fighter | 2 | anamol04 | 600 | 48 | 24 | 1.00 | 48.00 | 80 | 5 | 5 |
| fighter | 3 | uhla | 700 | 56 | 28 | 1.00 | 56.00 | 80 | 5 | 5 |
| fighter | 5 | galanonim | 900 | 72 | 36 | 1.00 | 72.00 | 80 | 5 | 5 |
| duelist | 1 | skibidi_kubus | 450 | 60 | 15 | 1.20 | 72.00 | 60 | 7 | 6 |
| duelist | 2 | kotmarcek | 540 | 72 | 18 | 1.20 | 86.40 | 60 | 7 | 6 |
| duelist | 3 | yossarian | 630 | 84 | 21 | 1.20 | 100.80 | 60 | 7 | 6 |
| duelist | 4 | alyson_stark | 720 | 96 | 24 | 1.20 | 115.20 | 60 | 7 | 6 |
| duelist | 5 | fiko | 810 | 108 | 27 | 1.20 | 129.60 | 60 | 7 | 6 |
| mage | 2 | chessowy_mentos | 480 | 36 | 12 | 0.90 | 32.40 | 40 | 10 | 8 |
| mage | 3 | aus_sher | 560 | 42 | 14 | 0.90 | 37.80 | 40 | 10 | 8 |
| mage | 4 | pytl | 640 | 48 | 16 | 0.90 | 43.20 | 40 | 10 | 8 |
| mage | 5 | szachowymentor | 720 | 54 | 18 | 0.90 | 48.60 | 40 | 10 | 8 |

## Economy audit

- Shop has 5 offer slots; reroll costs `2g`; buying XP costs `4g` for `4 XP`.
- XP contract: the live route and retained processor award exactly +2 XP for every completed combat, on both wins and losses.
- Approved income formula: `base 5 + interest min(5, gold//10 after win bonus) + win bonus 1 + fixed milestone 5g every fifth completed round`.
- Approved milestone contract: every fifth completed round grants fixed `5g`; round 3 grants exactly `3` item parts; other fifth-round milestones grant one base item part, with `+1` extra at round 10, `+2` at round 20, `+3` at round 30, and so on.
- Item parts are canonical `BASE_ITEMS` IDs appended to `PlayerState.item_inventory`, so the persisted inventory is the player-visible reward state.

| Shop level | Odds by cost | Expected cost/offer | Expected cost/5 offers |
|---:|---|---:|---:|
| 1 | {'1': 100} | 1.000 | 5.000 |
| 2 | {'1': 85, '2': 15} | 1.150 | 5.750 |
| 3 | {'1': 75, '2': 20, '3': 5} | 1.300 | 6.500 |
| 4 | {'1': 60, '2': 25, '3': 12, '4': 3} | 1.580 | 7.900 |
| 5 | {'1': 50, '2': 30, '3': 15, '4': 4, '5': 1} | 1.760 | 8.800 |
| 6 | {'1': 35, '2': 35, '3': 20, '4': 7, '5': 3} | 2.080 | 10.400 |
| 7 | {'1': 25, '2': 35, '3': 25, '4': 10, '5': 5} | 2.350 | 11.750 |
| 8 | {'1': 15, '2': 30, '3': 30, '4': 15, '5': 10} | 2.750 | 13.750 |
| 9 | {'1': 10, '2': 25, '3': 35, '4': 20, '5': 10} | 2.950 | 14.750 |
| 10 | {'1': 5, '2': 20, '3': 35, '4': 25, '5': 15} | 3.250 | 16.250 |

| Gold path | Gold after R3 | Gold after R5 | Gold after R10 | Gold after R15 | Gold after R20 | Parts after R3 | Parts after R5 | Parts after R10 | Parts after R15 | Parts after R20 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all_losses | 22 | 41 | 95 | 150 | 205 | 3 | 4 | 6 | 7 | 10 |
| all_wins | 24 | 46 | 105 | 165 | 225 | 3 | 4 | 6 | 7 | 10 |

## Issues found and order of operations

1. Preserve the approved economy contract while reviewing the remaining star-scaling and XP-path findings.
2. Re-run this audit after future rules changes; preserve the seeds and compare raw JSON results.
3. Only then review the per-unit proposals above. No unit values were edited by this audit.
4. Separately confirm whether `miki` and `atomowy_coggers` intentionally have no class.
5. Keep the stale 51-unit/14-trait documentation out of the balance source of truth; this report uses Python runtime and JSON data.

## Artifacts

- Raw machine-readable results: `docs\BALANCE_AUDIT_2026-09-12.json`.
- Re-run command: `python tools/balance_audit.py --generated-date 2026-09-12 --output-json docs\BALANCE_AUDIT_2026-09-12.json --output-md docs\BALANCE_AUDIT_2026-09-12.md`.

## Data vs interpretation

Data are the counts, win rates, formulas, and errors recorded in the JSON artifact. Labels, cutoff interpretation, and the proposed order of operations are audit judgments and should be reviewed before any patch.
