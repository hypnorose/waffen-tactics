# Waffen Tactics — Balance Audit

Generated: `2026-09-01`

## Executive summary

Runtime data contains **52 units** and **21 traits**. The audit ran **1000 team battles** (500 each for 5v5 and 10v10) and **2460 controlled same-cost pairwise simulations**.

Unit status counts: underpowered **19**, healthy **12**, overpowered **21**, insufficient data **0**.

The status is a screening signal, not an automatic balance patch. Pairwise data is primary; random-team data is reported separately because traits, composition, target selection, and side asymmetry confound it.

## Acceptance criteria

- Team battles: `1000/1000`; simulator errors: `0`; timeouts: `0`.
- Controlled pairwise errors: `0`; timeouts: `0`.
- Controlled trait threshold errors: `0`; threshold rows: `55`.
- Same-seed determinism probe: **PASS**.
- No game data or gameplay code is changed by this audit.

## Roster integrity

- Cost distribution: `{1: 11, 2: 11, 3: 10, 4: 9, 5: 11}`.
- Role distribution: `{'defender': 11, 'duelist': 12, 'fighter': 20, 'mage': 9}`.
- Duplicate unit IDs: `none`.
- Missing required fields: `none`.
- Invalid costs/roles: `none` / `none`.
- Units missing faction or class: `[{'unit_id': 'miki', 'missing': ['classes']}, {'unit_id': 'atomowy_coggers', 'missing': ['classes']}]`.
- Trait schema issues: `none`.
- Skill effect types: `{'buff': 16, 'conditional': 3, 'damage': 41, 'damage_over_time': 4, 'debuff': 14, 'delay': 4, 'heal': 7, 'shield': 8, 'stun': 9}`.

## Unit verdicts

Thresholds: pairwise win rate ≤35% = underpowered, ≥65% = overpowered; otherwise healthy. These cutoffs are intentionally conservative screening thresholds. Numeric value changes are not applied.

| Unit | Cost | Role | Pairwise | Team context | Sample | Status | Next action |
|---|---:|---|---:|---:|---:|---|---|
| adrianski | 4 | fighter | 43.8% | 54.2% | 80 | **healthy** | keep values and monitor after system-rule fixes |
| alyson_stark | 3 | fighter | 66.7% | 59.2% | 90 | **overpowered** | review for a nerf after system rules are normalized |
| atomowy_coggers | 4 | fighter | 43.8% | 44.5% | 80 | **healthy** | keep values and monitor after system-rule fixes |
| beligol | 5 | mage | 20.0% | 47.1% | 100 | **underpowered** | review for a buff after system rules are normalized |
| beudzik | 2 | fighter | 60.0% | 53.3% | 100 | **healthy** | keep values and monitor after system-rule fixes |
| bosman | 1 | fighter | 80.0% | 49.4% | 100 | **overpowered** | review for a nerf after system rules are normalized |
| buba | 2 | fighter | 75.0% | 50.9% | 100 | **overpowered** | review for a nerf after system rules are normalized |
| capybara | 3 | duelist | 88.9% | 53.0% | 90 | **overpowered** | review for a nerf after system rules are normalized |
| dawid_czerw | 2 | defender | 20.0% | 47.7% | 100 | **underpowered** | review for a buff after system rules are normalized |
| denvii | 5 | mage | 20.0% | 43.3% | 100 | **underpowered** | review for a buff after system rules are normalized |
| dumb | 1 | duelist | 100.0% | 47.7% | 100 | **overpowered** | review for a nerf after system rules are normalized |
| falconbalkon | 2 | fighter | 70.0% | 40.5% | 100 | **overpowered** | review for a nerf after system rules are normalized |
| fiko | 4 | defender | 25.0% | 54.7% | 80 | **underpowered** | review for a buff after system rules are normalized |
| flaminga | 3 | fighter | 44.4% | 47.9% | 90 | **healthy** | keep values and monitor after system-rule fixes |
| frajdzia | 3 | duelist | 94.4% | 59.6% | 90 | **overpowered** | review for a nerf after system rules are normalized |
| galanonim | 5 | fighter | 75.0% | 63.0% | 100 | **overpowered** | review for a nerf after system rules are normalized |
| grzalcia | 3 | mage | 11.1% | 40.5% | 90 | **underpowered** | review for a buff after system rules are normalized |
| hikki | 2 | fighter | 50.0% | 49.2% | 100 | **healthy** | keep values and monitor after system-rule fixes |
| hyodo888 | 2 | defender | 30.0% | 45.5% | 100 | **underpowered** | review for a buff after system rules are normalized |
| igor_janik | 3 | fighter | 50.0% | 49.1% | 90 | **healthy** | keep values and monitor after system-rule fixes |
| jaskol95 | 2 | duelist | 100.0% | 48.3% | 100 | **overpowered** | review for a nerf after system rules are normalized |
| krasu | 5 | duelist | 95.0% | 65.0% | 100 | **overpowered** | review for a nerf after system rules are normalized |
| kubica | 4 | duelist | 93.8% | 65.8% | 80 | **overpowered** | review for a nerf after system rules are normalized |
| laylo | 5 | mage | 20.0% | 51.1% | 100 | **underpowered** | review for a buff after system rules are normalized |
| maxas12 | 1 | fighter | 90.0% | 41.5% | 100 | **overpowered** | review for a nerf after system rules are normalized |
| merex | 4 | defender | 0.0% | 45.4% | 80 | **underpowered** | review for a buff after system rules are normalized |
| miki | 3 | duelist | 83.3% | 53.3% | 90 | **overpowered** | review for a nerf after system rules are normalized |
| mrozu | 1 | fighter | 65.0% | 41.6% | 100 | **overpowered** | review for a nerf after system rules are normalized |
| mrvlook | 1 | defender | 25.0% | 39.9% | 100 | **underpowered** | review for a buff after system rules are normalized |
| neko | 4 | defender | 12.5% | 48.3% | 80 | **underpowered** | review for a buff after system rules are normalized |
| noname | 3 | fighter | 33.3% | 54.4% | 90 | **underpowered** | review for a buff after system rules are normalized |
| olaczka | 5 | fighter | 60.0% | 57.4% | 100 | **healthy** | keep values and monitor after system-rule fixes |
| olsak | 1 | defender | 25.0% | 38.4% | 100 | **underpowered** | review for a buff after system rules are normalized |
| operatorkosiarki | 4 | duelist | 68.8% | 58.0% | 80 | **overpowered** | review for a nerf after system rules are normalized |
| pan_yakuza | 5 | fighter | 60.0% | 51.4% | 100 | **healthy** | keep values and monitor after system-rule fixes |
| pepe | 1 | mage | 0.0% | 33.3% | 100 | **underpowered** | review for a buff after system rules are normalized |
| piwniczak | 2 | mage | 0.0% | 33.7% | 100 | **underpowered** | review for a buff after system rules are normalized |
| puszmen12 | 4 | duelist | 93.8% | 66.6% | 80 | **overpowered** | review for a nerf after system rules are normalized |
| rafcikd | 1 | defender | 45.0% | 35.6% | 100 | **healthy** | keep values and monitor after system-rule fixes |
| socjopata | 2 | duelist | 90.0% | 46.0% | 100 | **overpowered** | review for a nerf after system rules are normalized |
| stalin | 5 | duelist | 95.0% | 72.4% | 100 | **overpowered** | review for a nerf after system rules are normalized |
| szachowymentor | 5 | mage | 0.0% | 52.4% | 100 | **underpowered** | review for a buff after system rules are normalized |
| szalwia | 5 | fighter | 65.0% | 64.1% | 100 | **overpowered** | review for a nerf after system rules are normalized |
| turboglovica | 3 | mage | 0.0% | 45.8% | 90 | **underpowered** | review for a buff after system rules are normalized |
| un4given | 1 | defender | 10.0% | 41.0% | 100 | **underpowered** | review for a buff after system rules are normalized |
| v7 | 1 | fighter | 65.0% | 44.9% | 100 | **overpowered** | review for a nerf after system rules are normalized |
| vitas | 3 | fighter | 27.8% | 48.6% | 90 | **underpowered** | review for a buff after system rules are normalized |
| wodazlodowca | 2 | defender | 10.0% | 43.4% | 100 | **underpowered** | review for a buff after system rules are normalized |
| wrzechu | 4 | duelist | 68.8% | 60.8% | 80 | **overpowered** | review for a nerf after system rules are normalized |
| wu_hao | 2 | fighter | 45.0% | 49.6% | 100 | **healthy** | keep values and monitor after system-rule fixes |
| xntentacion | 1 | defender | 45.0% | 45.4% | 100 | **healthy** | keep values and monitor after system-rule fixes |
| yossarian | 5 | mage | 40.0% | 50.7% | 100 | **healthy** | keep values and monitor after system-rule fixes |

## Role and cost results

| Group | Appearances | Wins | Win rate |
|---|---:|---:|---:|
| role: defender | 3082 | 1361 | 44.2% |
| role: duelist | 3554 | 2064 | 58.1% |
| role: fighter | 5816 | 2953 | 50.8% |
| role: mage | 2548 | 1122 | 44.0% |
| cost: 1 | 3139 | 1308 | 41.7% |
| cost: 2 | 3199 | 1476 | 46.1% |
| cost: 3 | 2852 | 1459 | 51.2% |
| cost: 4 | 2634 | 1465 | 55.6% |
| cost: 5 | 3176 | 1792 | 56.4% |

## Trait thresholds — controlled tests

Every authored threshold is listed. The trait team is compared with a same-size control team in both orientations. A tier with no valid controlled observations is `insufficient data`; these results must not drive a unit nerf/buff before system rules are normalized.

| Trait | Tier | Threshold | Decisive battles | Trait wins | Trait WR | Control WR | Delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| Srebrna Gwardia | 1 | 3 | 20 | 0 | 0.0% | 100.0% | -100.0% |
| Srebrna Gwardia | 2 | 5 | 20 | 0 | 0.0% | 100.0% | -100.0% |
| Srebrna Gwardia | 3 | 7 | 20 | 0 | 0.0% | 100.0% | -100.0% |
| Streamer | 1 | 2 | 20 | 0 | 0.0% | 100.0% | -100.0% |
| Streamer | 2 | 3 | 20 | 6 | 30.0% | 70.0% | -40.0% |
| Streamer | 3 | 4 | 20 | 5 | 25.0% | 75.0% | -50.0% |
| Streamer | 4 | 5 | 20 | 10 | 50.0% | 50.0% | 0.0% |
| XN Waffen | 1 | 3 | 20 | 12 | 60.0% | 40.0% | 20.0% |
| XN Waffen | 2 | 5 | 20 | 10 | 50.0% | 50.0% | 0.0% |
| XN Waffen | 3 | 7 | 20 | 8 | 40.0% | 60.0% | -20.0% |
| XN Waffen | 4 | 10 | 20 | 12 | 60.0% | 40.0% | 20.0% |
| XN KGB | 1 | 3 | 20 | 2 | 10.0% | 90.0% | -80.0% |
| XN KGB | 2 | 5 | 20 | 3 | 15.0% | 85.0% | -70.0% |
| XN KGB | 3 | 7 | 20 | 11 | 55.0% | 45.0% | 10.0% |
| XN KGB | 4 | 9 | 20 | 16 | 80.0% | 20.0% | 60.0% |
| Denciak | 1 | 2 | 20 | 2 | 10.0% | 90.0% | -80.0% |
| Denciak | 2 | 4 | 20 | 5 | 25.0% | 75.0% | -50.0% |
| Denciak | 3 | 6 | 20 | 4 | 20.0% | 80.0% | -60.0% |
| Starokurwy | 1 | 2 | 20 | 0 | 0.0% | 100.0% | -100.0% |
| Starokurwy | 2 | 3 | 20 | 2 | 10.0% | 90.0% | -80.0% |
| Starokurwy | 3 | 4 | 20 | 3 | 15.0% | 85.0% | -70.0% |
| Starokurwy | 4 | 5 | 20 | 2 | 10.0% | 90.0% | -80.0% |
| Prostaczka | 1 | 2 | 20 | 2 | 10.0% | 90.0% | -80.0% |
| Prostaczka | 2 | 4 | 20 | 9 | 45.0% | 55.0% | -10.0% |
| Prostaczka | 3 | 5 | 20 | 13 | 65.0% | 35.0% | 30.0% |
| Femboy | 1 | 2 | 20 | 14 | 70.0% | 30.0% | 40.0% |
| Femboy | 2 | 3 | 20 | 16 | 80.0% | 20.0% | 60.0% |
| Femboy | 3 | 4 | 20 | 13 | 65.0% | 35.0% | 30.0% |
| Femboy | 4 | 5 | 20 | 17 | 85.0% | 15.0% | 70.0% |
| Szachista | 1 | 2 | 20 | 2 | 10.0% | 90.0% | -80.0% |
| Szachista | 2 | 3 | 20 | 10 | 50.0% | 50.0% | 0.0% |
| Szachista | 3 | 4 | 20 | 7 | 35.0% | 65.0% | -30.0% |
| Spell | 1 | 3 | 20 | 9 | 45.0% | 55.0% | -10.0% |
| Spell | 2 | 5 | 20 | 5 | 25.0% | 75.0% | -50.0% |
| Spell | 3 | 7 | 20 | 6 | 30.0% | 70.0% | -40.0% |
| Konfident | 1 | 2 | 20 | 18 | 90.0% | 10.0% | 80.0% |
| Konfident | 2 | 4 | 20 | 13 | 65.0% | 35.0% | 30.0% |
| Konfident | 3 | 6 | 20 | 18 | 90.0% | 10.0% | 80.0% |
| Haker | 1 | 3 | 20 | 2 | 10.0% | 90.0% | -80.0% |
| Haker | 2 | 5 | 20 | 1 | 5.0% | 95.0% | -90.0% |
| Haker | 3 | 7 | 20 | 0 | 0.0% | 100.0% | -100.0% |
| Gamer | 1 | 3 | 20 | 10 | 50.0% | 50.0% | 0.0% |
| Gamer | 2 | 5 | 20 | 12 | 60.0% | 40.0% | 20.0% |
| Gamer | 3 | 7 | 20 | 10 | 50.0% | 50.0% | 0.0% |
| Gamer | 4 | 9 | 20 | 10 | 50.0% | 50.0% | 0.0% |
| Normik | 1 | 2 | 20 | 0 | 0.0% | 100.0% | -100.0% |
| Normik | 2 | 4 | 20 | 1 | 5.0% | 95.0% | -90.0% |
| Normik | 3 | 5 | 20 | 0 | 0.0% | 100.0% | -100.0% |
| Hitman | 1 | 1 | 20 | 13 | 65.0% | 35.0% | 30.0% |
| Wygnaniec | 1 | 1 | 20 | 10 | 50.0% | 50.0% | 0.0% |
| XN Jugend | 1 | 1 | 20 | 10 | 50.0% | 50.0% | 0.0% |
| XN Mod | 1 | 1 | 20 | 20 | 100.0% | 0.0% | 100.0% |
| XN Monter | 1 | 1 | 20 | 11 | 55.0% | 45.0% | 10.0% |
| XN HomoKomando | 1 | 1 | 20 | 10 | 50.0% | 50.0% | 0.0% |
| XN Yakuza | 1 | 1 | 20 | 18 | 90.0% | 10.0% | 80.0% |

## Stat budget and star scaling

The runtime currently scales HP by ×1.6 and attack by ×1.4 per star step; defense, attack speed, and max mana remain at base values. See the JSON artifact for every role/cost row and 1★/2★/3★ values.

| Role | Cost | Representative | HP | Attack | Defense | Speed | DPS | Max mana | Mana/attack | Regen |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| defender | 1 | rafcikd | 600 | 30 | 30 | 0.80 | 24.00 | 100 | 4 | 4 |
| defender | 2 | hyodo888 | 720 | 36 | 36 | 0.80 | 28.80 | 100 | 4 | 4 |
| defender | 4 | merex | 960 | 48 | 48 | 0.80 | 38.40 | 100 | 4 | 4 |
| fighter | 1 | maxas12 | 500 | 40 | 20 | 1.00 | 40.00 | 80 | 5 | 5 |
| fighter | 2 | falconbalkon | 600 | 48 | 24 | 1.00 | 48.00 | 80 | 5 | 5 |
| fighter | 3 | igor_janik | 700 | 56 | 28 | 1.00 | 56.00 | 80 | 5 | 5 |
| fighter | 4 | adrianski | 800 | 64 | 32 | 1.00 | 64.00 | 80 | 5 | 5 |
| fighter | 5 | olaczka | 900 | 72 | 36 | 1.00 | 72.00 | 80 | 5 | 5 |
| duelist | 1 | dumb | 450 | 60 | 15 | 1.20 | 72.00 | 60 | 7 | 6 |
| duelist | 2 | jaskol95 | 540 | 72 | 18 | 1.20 | 86.40 | 60 | 7 | 6 |
| duelist | 3 | capybara | 630 | 84 | 21 | 1.20 | 100.80 | 60 | 7 | 6 |
| duelist | 4 | kubica | 720 | 96 | 24 | 1.20 | 115.20 | 60 | 7 | 6 |
| duelist | 5 | stalin | 810 | 108 | 27 | 1.20 | 129.60 | 60 | 7 | 6 |
| mage | 1 | pepe | 400 | 30 | 10 | 0.90 | 27.00 | 40 | 10 | 8 |
| mage | 2 | piwniczak | 480 | 36 | 12 | 0.90 | 32.40 | 40 | 10 | 8 |
| mage | 3 | grzalcia | 560 | 42 | 14 | 0.90 | 37.80 | 40 | 10 | 8 |
| mage | 5 | denvii | 720 | 54 | 18 | 0.90 | 48.60 | 40 | 10 | 8 |

## Economy audit

- Shop has 5 offer slots; reroll costs `2g`; buying XP costs `4g` for `4 XP`.
- XP path discrepancy: the live route grants +2 XP per combat, while the helper adds another +2 XP on wins (4 XP on a win).
- Current milestone formula: `base 5 + interest min(5, gold//10) + win bonus 1 + milestone equal to round number every fifth round`. This is a runaway-economy risk at later rounds and is recorded for system-level correction before unit tuning.

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

## Issues found and order of operations

1. Normalize system rules first: star scaling contract, XP parity between live route and helper, and milestone economy.
2. Re-run this audit after those fixes; preserve the seeds and compare raw JSON results.
3. Only then review the per-unit proposals above. No unit values were edited by this audit.
4. Separately confirm whether `miki` and `atomowy_coggers` intentionally have no class.
5. Keep the stale 51-unit/14-trait documentation out of the balance source of truth; this report uses Python runtime and JSON data.

## Artifacts

- Raw machine-readable results: `docs/BALANCE_AUDIT_2026-09-01.json`.
- Re-run command: `python tools/balance_audit.py`.

## Data vs interpretation

Data are the counts, win rates, formulas, and errors recorded in the JSON artifact. Labels, cutoff interpretation, and the proposed order of operations are audit judgments and should be reviewed before any patch.
