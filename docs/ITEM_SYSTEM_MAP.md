# Waffen Tactics — item system map

Date: 2026-09-10  
Scope: Waffen Tactics 2 / approved Set 2 item content

This document is a handoff map for the active canonical pipeline. Plane remains
the source of truth for issue state and author decisions.

## Authority and gates

| Area | Source / owner | Current state |
| --- | --- | --- |
| Recipe content | WFT-139, Plane comment `58175dd5-e14e-49f5-8ffe-359fa02bca56` | **Approved**: 6 bases, 21 recipes, including 6 A+A pairs |
| Human-readable matrix | [`ITEM_RECIPE_MATRIX_WFT139.md`](ITEM_RECIPE_MATRIX_WFT139.md) | Approved content copy |
| Structured content copy | [`waffen-tactics/item_recipe_matrix_wft139.json`](../waffen-tactics/item_recipe_matrix_wft139.json) | Approved canonical runtime/API source |
| Runtime effect contract | WFT-140, Plane comment `c7b4c2eb-9cc2-49a7-9c13-19b7a7ffda3e` | **Done**: deterministic order, refresh/replace default, explicit caps, reset, RNG and replay rules |
| Seeded content/contract checks | WFT-149 | `Todo`; 6 tests cover the approved 6+21 matrix and accepted runtime contract |
| Canonical runtime source | WFT-141 | `In Progress`; loader, actions, backend projection and frontend catalog migration |

WFT-139 approval replaces the earlier AI-generated recipe proposal as the content
source. WFT-140 supplies the accepted prototype runtime semantics. WFT-141 now
loads the approved matrix for shared runtime/API/frontend projections; combat
effect execution and deployment evidence remain separate follow-up gates.

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

The following paths describe the current runtime boundaries:

- `waffen-tactics/src/waffen_tactics/services/items.py` loads and validates the
  approved JSON, then exports derived `BASE_ITEMS`, `ITEMS` and `RECIPES` views.
- `waffen-tactics-web/backend/services/item_actions.py` validates equip and
  manual combine against that canonical lookup, including A+A recipes; auto-combine
  is not yet wired.
- `waffen-tactics-web/backend/routes/game_actions.py` and `game_routes.py` expose the
  existing item catalog/equip/combine endpoints.
- `waffen-tactics/src/waffen_tactics/services/combat_manager.py` applies the shared
  item-stat helper and carries the structured effect payload for later execution.
- `waffen-tactics-web/backend/routes/game_state_utils.py` uses the same item-stat
  helper for the displayed unit projection.
- `waffen-tactics-web/src/data/items.ts` now contains only typed API data helpers
  and presentation icons; `ItemsPanel.tsx`, `EquippedItems.tsx` and `UnitCard.tsx`
  consume the backend catalog rather than a second name/stat/description source.
- `waffen-tactics/src/waffen_tactics/services/economy.py` awards base-item IDs to
  `PlayerState.item_inventory`; this reward boundary remains unchanged until the
  canonical migration is implemented.

No Set 2 implementation should assume that combined items inherit component stat
packages. The approved matrix gives each result its own explicit listed stats and
effect prose; the combat implementation still must make every behavior explicit.

## Verification boundary

- `waffen-tactics/tests/test_wft139_recipe_matrix.py` verifies the approved matrix
  and accepted contract: 6 bases, all 21 unordered pairs, A+A, symmetric lookup,
  exact names/stats/effect descriptions, explicit caps and per-fight reset.
- `waffen-tactics/tests/test_items.py` verifies that the active runtime exports
  exactly 6 bases and 21 canonical recipes, accepts A+A, and applies stats through
  the shared helper. Backend and frontend tests cover the catalog/action boundary.
- These automated checks do not prove live deployment, authenticated frontend
  presentation, SSE or replay acceptance. Those require the corresponding
  WFT-142–WFT-148 work and runtime evidence.

## Explicit non-goals of this map

- Do not add a second item name/stat/effect source outside the approved matrix.
- Do not invent missing trigger/target/scope/order/stacking/RNG/replay contracts.
- Do not treat item effect metadata as fully executed combat behavior before the
  WFT-142–WFT-147 runtime/effect gates are complete.
