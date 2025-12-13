from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Stats:
    attack: int
    hp: int
    defense: int
    max_mana: int
    attack_speed: float  # attacks per second

    def get(self, key: str, default=None):
        """Compatibility helper: allow dict-like `.get` access for Stats.

        Some older code paths expect unit.stats to be a mapping and call
        `.get(key, default)`. Provide that interface to avoid runtime
        errors while keeping `Stats` a typed dataclass.
        """
        return getattr(self, key, default)

@dataclass
class Skill:
    name: str
    description: str
    mana_cost: int
    # For now, effect is a simple dict placeholder
    effect: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Unit:
    id: str
    name: str
    cost: int
    factions: List[str]
    classes: List[str]
    stats: Stats
    skill: Skill
    avatar: str = ""

    @staticmethod
    def from_json(d: Dict[str, Any], default_stats: Stats, default_skill: Skill) -> "Unit":
        return Unit(
            id=d["id"],
            name=d["name"],
            cost=int(d["cost"]),
            factions=list(d.get("factions", [])),
            classes=list(d.get("classes", [])),
            stats=default_stats,
            skill=default_skill,
            avatar=d.get("avatar", ""),
        )
