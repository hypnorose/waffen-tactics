# Legacy set archive — 2026-09-04

This directory is a byte-for-byte snapshot of the active Waffen Tactics set
before designing the next set. The archive is reference-only; the running game
still reads the files under `waffen-tactics/`.

## Archived content

- `units.json` — 52 unit definitions, including legacy skill descriptions and
  effect graphs.
- `traits.json` — 21 traits: 6 factions and 15 classes.
- `unit_roles.json` — the four role stat/mana profiles.
- `passive_definitions.py` — the runtime passive definitions used by the
  current combat ruleset.
- `BALANCE_AUDIT_2026-09-01.md` and `.json` — the existing read-only balance
  snapshot, when the files were present.

SHA-256 checksums:

| File | SHA-256 |
|---|---|
| `units.json` | `C23E3DDA1144F4D0E9A08D6A3E7C3564973D83152E43E9A1CA8A2A3A9496B837` |
| `traits.json` | `C5C725992EAFA78260AADE1AAD801097B845E4612F789F23797E81EA7339C0A5` |
| `unit_roles.json` | `D43205BF204AB062D1CE9B7AAD07FB0F90846F3E68EF69584BAC81C2ED065910` |
| `passive_definitions.py` | `1ABDE14B23A22B146F4D8A2F8BEEF91A00E0C9AA99DF6D8D132A4B2ABCE00220` |
| `BALANCE_AUDIT_2026-09-01.json` | `1781FADD80053FF41CEE7D4B0B5608647B256326E0CAB52DB1707692709E9E2F` |
| `BALANCE_AUDIT_2026-09-01.md` | `B79D9BBD6C5E21D91BE34749205C8BCAE41349DD26098415E477D0BCE1EC929C` |

## How the legacy set worked

### Data and loading

`waffen-tactics/units.json` is the roster source of truth. `services/data_loader.py`
loads it together with `traits.json` and `unit_roles.json`. A unit's role
selects its base HP, attack, defense, attack speed and mana profile; cost then
scales HP, attack and defense by `1 + 0.2 * (cost - 1)`. Runtime mana values
come from the role profile, not from the serialized skill description.

The loaded `Unit` keeps a parsed legacy `skill`, but every loaded unit also
receives a separate passive definition from `passive_definitions.py`.

### Traits

`SynergyEngine.compute()` counts unique unit IDs, then activates the highest
threshold reached for each faction/class. `apply_stat_buffs()` handles static
stat rewards and target scope; `apply_dynamic_effects()` handles win/loss
scaling. Legacy effect objects and the newer trigger/reward (`modular_effects`)
shape are both supported.

The trait guide documents the available trigger vocabulary (`passive`, death,
per-second, per-round, HP threshold, win/loss and related triggers) and reward
types. New content should keep the JSON schema and runtime handler names in
sync unless a new set explicitly includes a system migration.

### Combat behavior

Normal combat is owned by `CombatManager` and the shared
`services/combat_simulator.py` pipeline. The current ruleset initializes
passives, applies per-round/per-second effects and regeneration, then performs
basic attacks. The normal loop does **not** invoke `skill_executor`; full mana
produces a bonus basic attack and resets the mana bar rather than emitting a
normal `skill_cast`.

`PassiveProcessor` is therefore the active unit-behavior system. It supports
start-of-combat effects, target preferences, attack counters, bonus-attack
modifiers, HP thresholds and kill triggers. There are 16 passive kinds in the
snapshot; 13 units have bonus-attack passives, 9 use attack counters, and 4
have explicit front/back position branches.

### Position and targeting

Player `UnitInstance.position` is preserved when `CombatManager` creates the
combat unit. The current opponent construction path forces every opponent to
`position='front'`; the compatibility wrapper also creates both sides as
front-line units. This is a known limitation and is important when designing
the new set: positional diversity cannot be evaluated as a real opponent
composition until opponent placement is made data-driven.

Basic target selection prefers living front-line targets, then back-line
targets. It can honor passive preferences such as backline, frontline or
lowest HP, and it keeps a living focus target until that target dies. The
legacy `SkillExecutor` has separate `enemy_front`/`ally_front` handlers, but
those legacy handlers select the first three living units rather than filtering
the `position` field; this is not the normal passive combat path.

### Important distinction for the next set

The old JSON contains 14 skills whose authored effects are defensive/support
only (shield, buff, heal and/or debuff without damage). That is not by itself a
runtime no-op: normal combat uses the unit's passive and basic attack, while
the legacy skill graph is currently not cast by the normal simulator. Future
audits must report separately:

1. no legal runtime action;
2. a deliberate defensive/support action;
3. repeated basic behavior with no variation;
4. missing position or targeting support;
5. an authored skill effect that is unreachable in the current ruleset.

## Provenance and migration rule

This snapshot was made on 2026-09-04 from the working tree. Existing unrelated
working-tree changes were not modified. When the new set is ready, keep this
directory immutable and record the new active source files plus a migration
note; do not overwrite the archive in place.
