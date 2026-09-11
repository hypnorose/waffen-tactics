# WFT-158: Set 2 active roster boundary

The active Waffen Tactics runtime loads its canonical content from:

- `waffen-tactics/units.json` — exactly 32 units
- `waffen-tactics/traits.json` — exactly 12 traits

The previous roster is historical reference material only. It is not a
runtime fallback and must not be repaired by mapping old IDs to new IDs.
Historical files remain under `archive/sets/legacy-2026-09-04/`.

## State boundary

Player board, bench, locked shop, and combat team entries must resolve to an
ID in the active Set 2 roster. Unknown or removed IDs fail closed before a
state projection or mutation. The same rule applies to opponent combat teams.

When an old saved state is encountered, the safe recovery is to reset or
explicitly migrate that state outside the request path. The runtime never
silently maps, drops, or partially renders an unknown unit.

The loader also verifies the complete Set 2 dataset and rejects any unit that
references a trait missing from the active trait source.
