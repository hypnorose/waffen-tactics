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

## Periodic buff controls

`CombatSimulator.simulate` exposes two independent switches:

* `skip_per_round_buffs` skips start-of-combat modular and legacy per-round
  effects.
* `skip_per_second_buffs` skips modular, passive, and legacy per-second
  effects.

HP/mana regeneration is a separate subsystem and is not controlled by either
  switch. Live combat, replay generation, and the balance audit explicitly
  skip per-round effects while allowing per-second effects, so they share the
  same intentional timing contract.

## Stat-buff recipient boundary

`CombatEffectProcessor._apply_stat_buff` has one authoritative path for
recipient resolution and stat application. The accepted targets in this
legacy action path are:

* `self`: the source unit;
* `team`: living units from the explicit team matching `side`;
* `board`: living units from both explicit teams, in attacking-team then
  defending-team order.

An explicit empty team or board is a valid no-recipient result. Missing team
context, an invalid side for `team`, and unsupported targets fail closed with
an explicit runtime error; they never fall back to `self`. The modular runtime
continues to own its separate `trait` target vocabulary.

All registered stat buffs, including `lifesteal`, `damage_reduction`, and
`hp_regen_per_sec`, use the same handler registry. Stat validation occurs
before recipient mutation, and percentage values are converted to one
absolute increment before the handler runs, preventing double application.
HP-list mirrors are selected by the actual recipient team, including board
effects that reach the opposing team. No dataset or 32-unit content contract
is changed by this boundary.

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
