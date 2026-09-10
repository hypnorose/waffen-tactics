# Waffen Tactics — WFT-150 Item Balance Audit

- Generated: `2026-09-11`
- Content source: `WFT-139` / `wft139-approved-2026-09-10`
- Content seed: `wft139-approved-2026-09-10`
- Runtime measurement: **INSUFFICIENT-DATA** — item effects are not yet executed by the canonical combat runtime.

## Contract evidence

- Contract validation: **PASS**
- Bases: `6`; recipes: `21`; A+A recipes: `6`.
- No authored stat or effect value was changed by this audit.

## Simulation gate

Pairwise and team simulations were not run because a stat-only run would omit the approved dynamic effects and produce misleading balance evidence.

| Item | Static flags | Stat review | Effect review | Author decision |
| --- | --- | --- | --- | --- |
| etf_przyprawowy | +30_attack | contract-review | insufficient-data | pending |
| helena_o_smaku_kurkumy | — | contract-review | insufficient-data | pending |
| plaszcz_ze_100_bawelny | — | contract-review | insufficient-data | pending |
| skrytka_na_oregano | — | contract-review | insufficient-data | pending |
| ponetne_stopki | — | contract-review | insufficient-data | pending |
| pikante_slowka | lifesteal | contract-review | insufficient-data | pending |
| mandarynkowy_sodastream | — | contract-review | insufficient-data | pending |
| bluza_z_bytom | — | contract-review | insufficient-data | pending |
| kolekcja_syropow | 20_mana_per_second | contract-review | insufficient-data | pending |
| kremik_owocowy | multi_target | contract-review | insufficient-data | pending |
| telewizor_4k_50_cali | — | contract-review | insufficient-data | pending |
| plaszcz_200_welny | +600_hp | contract-review | insufficient-data | pending |
| forteca_z_ksiazek | — | contract-review | insufficient-data | pending |
| fartuszek_femboya | — | contract-review | insufficient-data | pending |
| full_plate_cum_armor | 2pct_max_hp_per_second | contract-review | insufficient-data | pending |
| skruszony_zab | reflect | contract-review | insufficient-data | pending |
| zestaw_do_makijazu_po_edycie | stack_cap_10 | contract-review | insufficient-data | pending |
| fap_folder | stack_cap_30 | contract-review | insufficient-data | pending |
| stopki_rozmiar_44 | multi_target | contract-review | insufficient-data | pending |
| idealny_traf | — | contract-review | insufficient-data | pending |
| encyklopedia_seksu | — | contract-review | insufficient-data | pending |

## Next gate

After WFT-142, WFT-143, WFT-144 and WFT-145 expose deterministic item execution through the shared combat path, rerun this audit with real combat seeds, pairwise/team counts, confidence markers and expected-vs-actual scenarios.
