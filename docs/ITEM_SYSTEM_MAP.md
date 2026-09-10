# Waffen Tactics — item system map

Date: 2026-09-10  
Scope: Waffen Tactics 2 / approved Set 2 item content

This document is a handoff map, not an active runtime dataset. Plane remains the
source of truth for issue state and author decisions.

## Authority and gates

| Area | Source / owner | Current state |
| --- | --- | --- |
| Recipe content | WFT-139, Plane comment `58175dd5-e14e-49f5-8ffe-359fa02bca56` | **Approved**: 6 bases, 21 recipes, including 6 A+A pairs |
| Human-readable matrix | [`ITEM_RECIPE_MATRIX_WFT139.md`](ITEM_RECIPE_MATRIX_WFT139.md) | Approved content copy |
| Structured content copy | [`waffen-tactics/item_recipe_matrix_wft139.json`](../waffen-tactics/item_recipe_matrix_wft139.json) | Approved content; not loaded by runtime |
| Runtime effect contract | WFT-140, Plane comment `c7b4c2eb-9cc2-49a7-9c13-19b7a7ffda3e` | **Done**: deterministic order, refresh/replace default, explicit caps, reset, RNG and replay rules |
| Seeded content/contract checks | WFT-149 | `In Progress`; 6 tests cover the approved 6+21 matrix and accepted runtime contract |
| Canonical runtime source | WFT-141 | Backlog; owns later backend/frontend source unification |

WFT-139 approval replaces the earlier AI-generated recipe proposal as the content
source. WFT-140 now supplies the accepted prototype runtime semantics. Neither
approval activates the records in the deployed runtime or finalizes balance.

## Planned canonical pipeline

| Stage | Plane work | Responsibility |
| --- | --- | --- |
| 1. Content | WFT-139 | Approved base items, recipe pairs, names, stats, effect prose and interpretation rules |
| 2. Contract | WFT-140 | Explicit effect family, trigger, target, scope, order, duration, stacking/cap, reset, RNG and replay fields |
| 3. Data source | WFT-141 | One canonical matrix for shared core, backend payloads and frontend catalog data |
| 4. Actions | WFT-138 | Combine/equip/auto-combine using only the canonical matrix, including A+A and fail-closed missing pairs |
| 5. Combat | WFT-142, WFT-143, WFT-144, WFT-145 | Apply item stats and effects through the shared authoritative combat path |
| 6. Events/replay | WFT-147 | Preserve canonical item/effect state through SSE, snapshots and replay |
| 7. Presentation | WFT-146 | Catalog, tooltips, equipped items and player-facing effect details |
| 8. Persistence | WFT-148 | Validate legal item IDs and separate persistent loadout from per-fight state |

The order above is the intended handoff sequence. The WFT-140 contract gate is
closed; runtime work still must pass through WFT-141's canonical-source gate.

## Legacy runtime boundary

The following paths describe the currently deployed/prototype infrastructure. They
are reference points for migration, not the approved Set 2 recipe source:

- `waffen-tactics/src/waffen_tactics/services/items.py` currently exports the old
  `BASE_ITEMS`, `_RECIPES`, `ITEMS` and `RECIPES` definitions.
- `waffen-tactics-web/backend/services/item_actions.py` currently validates equip and
  manual combine against that legacy `ITEMS` lookup; auto-combine is not yet wired.
- `waffen-tactics-web/backend/routes/game_actions.py` and `game_routes.py` expose the
  existing item catalog/equip/combine endpoints.
- `waffen-tactics/src/waffen_tactics/services/combat_manager.py` applies the current
  item stats and descriptive effects to combat units.
- `waffen-tactics-web/backend/routes/game_state_utils.py` enriches displayed unit
  stats from the current item lookup.
- `waffen-tactics-web/src/data/items.ts`, `ItemsPanel.tsx`, `EquippedItems.tsx` and
  `UnitCard.tsx` are the current frontend catalog/presentation owners and must be
  migrated through WFT-141/WFT-146 rather than maintained as a second Set 2 source.
- `waffen-tactics/src/waffen_tactics/services/economy.py` awards base-item IDs to
  `PlayerState.item_inventory`; this reward boundary remains unchanged until the
  canonical migration is implemented.

No Set 2 implementation should assume that combined items inherit component stat
packages. The approved matrix gives each result its own explicit listed stats and
effect prose; the final runtime contract must make every behavior explicit.

## Verification boundary

- `waffen-tactics/tests/test_wft139_recipe_matrix.py` verifies the approved matrix
  and accepted contract: 6 bases, all 21 unordered pairs, A+A, symmetric lookup,
  exact names/stats/effect descriptions, explicit caps and per-fight reset.
- The shared-core gate after this documentation/data slice is **573 passed, 25
  skipped, 22 subtests passed**.
- These automated checks do not prove live runtime, frontend presentation, SSE or
  replay acceptance. Those require the corresponding WFT-142–WFT-148 work and
  runtime evidence.

## Explicit non-goals of this map

- Do not edit legacy `items.py` or frontend item data as part of documentation work.
- Do not invent missing trigger/target/scope/order/stacking/RNG/replay contracts.
- Do not treat the structured JSON copy as active production data before WFT-141 is
  complete.
