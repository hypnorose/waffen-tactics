# Combat Runtime Ownership Boundary

Date: 2026-09-09

Plane project: `Waffen Tactics` (`WFT`). Current status and contract decisions are authoritative in Plane; the `DEF-*` identifiers below are historical imported references.

## Production owner

Production web combat follows this path:

```text
backend.services.combat_service.run_combat_simulation
    -> waffen_tactics.services.combat_shared.CombatSimulator
    -> waffen_tactics.services.combat_simulator.CombatSimulator
```

The shared services simulator owns production combat state, attack processing,
passives, canonical event emission, and replay-facing authoritative values.
The backend route must delegate through the service owner and must not create a
second simulator implementation.

## Quarantined compatibility surfaces

`waffen_tactics.core.combat_core` and
`waffen_tactics.processors.attack.CombatAttackProcessor` are retained only for
existing compatibility/animation tests. They are not the production combat
authority and currently expose a different prototype damage contract.

`waffen_tactics.services.combat` is a legacy `Unit`-shaped CLI adapter that
delegates to the shared services simulator; it is not an alternate production
web path.

## Change rules

* Do not import `core.combat_core` or `processors.attack` from production
  runtime code.
* Do not change the prototype formula to tune live gameplay.
* Do not migrate or delete the compatibility surfaces until the approved
  damage/core-extraction contract is recorded in Plane.
* Do not change content, balance values, or the legacy archive as part of
  boundary enforcement.

The import guard in
`waffen-tactics-web/backend/tests/test_combat_call_path.py` mechanically
protects the production boundary.
