"""Canonical system-opponent encounter definitions.

The progression values in this module preserve the existing system-opponent
ladder.  They are shared by startup seeding and the controlled Set 2 database
migration so the two paths cannot silently drift apart.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Sequence
import random


SYSTEM_USER_MAX = 100_000
DEFAULT_ENCOUNTER_SEED = 167


@dataclass(frozen=True)
class SystemEncounterDefinition:
    """One authored system encounter profile."""

    user_id: int
    nickname: str
    wins: int
    losses: int
    level: int
    team_size: int
    star_level: int


# Keep this ladder byte-for-byte equivalent in meaning to the pre-cutover
# sample_opponents list.  Set 2 migration changes only the unit IDs selected
# for these existing profiles.
SYSTEM_ENCOUNTER_DEFINITIONS = (
    SystemEncounterDefinition(1, "🆕 Tutorial Bot", 0, 1, 1, 1, 1),
    SystemEncounterDefinition(2, "🎯 Practice Dummy", 1, 1, 1, 1, 1),
    SystemEncounterDefinition(3, "🌱 Rookie Fighter", 2, 1, 1, 1, 1),
    SystemEncounterDefinition(4, "🔰 Beginner", 3, 1, 2, 2, 1),
    SystemEncounterDefinition(5, "🦾 Young Gun", 4, 1, 2, 2, 1),
    SystemEncounterDefinition(6, "🦆 Duckling", 5, 1, 2, 2, 1),
    SystemEncounterDefinition(7, "🥉 Bronze Bot", 6, 2, 3, 3, 1),
    SystemEncounterDefinition(8, "⚔️ Bronze Fighter", 7, 2, 3, 3, 1),
    SystemEncounterDefinition(9, "🛡️ Bronze Guard", 8, 2, 3, 3, 1),
    SystemEncounterDefinition(10, "🔱 Bronze Elite", 9, 3, 4, 4, 1),
    SystemEncounterDefinition(11, "🥈 Silver Bot", 10, 3, 4, 4, 1),
    SystemEncounterDefinition(12, "⚡ Silver Storm", 11, 3, 4, 4, 1),
    SystemEncounterDefinition(13, "🌟 Silver Star", 12, 4, 5, 5, 1),
    SystemEncounterDefinition(14, "👑 Silver King", 13, 4, 5, 5, 1),
    SystemEncounterDefinition(15, "🦁 Silver Lion", 14, 4, 5, 5, 1),
    SystemEncounterDefinition(16, "🥇 Gold Bot", 15, 5, 6, 6, 1),
    SystemEncounterDefinition(17, "💫 Gold Ace", 16, 5, 6, 6, 1),
    SystemEncounterDefinition(18, "🔥 Gold Blaze", 17, 5, 6, 6, 1),
    SystemEncounterDefinition(19, "⭐ Gold Legend", 18, 6, 7, 7, 1),
    SystemEncounterDefinition(20, "🦅 Gold Eagle", 19, 6, 7, 7, 1),
    SystemEncounterDefinition(21, "💎 Platinum Pro", 20, 6, 7, 7, 1),
    SystemEncounterDefinition(22, "🏆 Platinum Ace", 21, 7, 8, 8, 1),
    SystemEncounterDefinition(23, "👾 Platinum Cyborg", 22, 7, 8, 8, 1),
    SystemEncounterDefinition(24, "🦍 Platinum Gorilla", 23, 7, 8, 8, 1),
    SystemEncounterDefinition(25, "👹 Diamond Beast", 24, 8, 9, 9, 1),
    SystemEncounterDefinition(26, "💀 Diamond Skull", 25, 8, 9, 9, 1),
    SystemEncounterDefinition(27, "🦾 Diamond Titan", 26, 8, 9, 9, 1),
    SystemEncounterDefinition(28, "👽 Alien Overlord", 27, 9, 10, 10, 1),
    SystemEncounterDefinition(29, "🐉 Dragon Lord", 28, 9, 10, 10, 1),
    SystemEncounterDefinition(30, "🦸‍♂️ Heroic Bot", 29, 9, 10, 10, 1),
    SystemEncounterDefinition(31, "🤖 Supreme AI", 30, 10, 10, 10, 1),
    SystemEncounterDefinition(32, "💀 MegaBot X", 31, 10, 10, 12, 2),
    SystemEncounterDefinition(33, "👾 OmegaBot", 35, 11, 10, 14, 2),
    SystemEncounterDefinition(34, "👑 Kingpin AI", 40, 13, 10, 16, 2),
    SystemEncounterDefinition(35, "🦾 Iron Colossus", 45, 15, 10, 18, 3),
    SystemEncounterDefinition(36, "👑 UltraBot Prime", 50, 16, 10, 20, 3),
    SystemEncounterDefinition(37, "🦾 Omega Colossus", 60, 20, 10, 24, 3),
    SystemEncounterDefinition(38, "👑 Legendarny AI", 80, 26, 10, 30, 3),
)


def _field(unit: Any, name: str) -> Any:
    if isinstance(unit, Mapping):
        return unit.get(name)
    return getattr(unit, name, None)


def build_system_opponent_payloads(
    units: Sequence[Any],
    *,
    seed: int = DEFAULT_ENCOUNTER_SEED,
) -> list[dict[str, Any]]:
    """Build deterministic persisted teams from the active unit dataset.

    The selection policy matches the previous cost-biased generator, but uses
    a local seeded RNG instead of mutating process-global random state.
    """

    unit_records = [
        {"id": _field(unit, "id"), "cost": _field(unit, "cost")}
        for unit in units
    ]
    if not unit_records or any(
        not isinstance(unit["id"], str) or not unit["id"].strip()
        or not isinstance(unit["cost"], int)
        for unit in unit_records
    ):
        raise ValueError("System encounters require units with string IDs and integer costs")
    ids = [unit["id"] for unit in unit_records]
    if len(ids) != len(set(ids)):
        raise ValueError("System encounters require unique unit IDs")

    payloads = []
    for definition in SYSTEM_ENCOUNTER_DEFINITIONS:
        rng = random.Random(seed + definition.user_id * 1_000_003)
        desired_cost = max(
            1,
            min(5, definition.star_level + (definition.level - 1) // 4),
        )
        available = list(unit_records)
        selected = []
        for _ in range(min(definition.team_size, len(available))):
            candidates = [
                unit for unit in available
                if abs(unit["cost"] - desired_cost) <= 1
            ] or available
            weights = []
            for unit in candidates:
                closeness = 1.0 / (1 + abs(unit["cost"] - desired_cost))
                cost_preference = 1.0 + (unit["cost"] - desired_cost) * 0.15
                weights.append(max(0.01, closeness * cost_preference))
            chosen = rng.choices(candidates, weights=weights, k=1)[0]
            selected.append(chosen)
            available.remove(chosen)

        payloads.append({
            "user_id": definition.user_id,
            "nickname": definition.nickname,
            "board_units": [
                {"unit_id": unit["id"], "star_level": definition.star_level}
                for unit in selected
            ],
            "bench_units": [],
            "wins": definition.wins,
            "losses": definition.losses,
            "level": definition.level,
        })
    return payloads
