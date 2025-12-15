from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Stats:
    attack: int
    hp: int
    defense: int
    max_mana: int
    attack_speed: float  # attacks per second
    mana_on_attack: int = 10  # mana gained per attack
    mana_regen: int = 5  # mana regenerated per turn

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
    role: str = ""
    role_color: str = "#6b7280"
    avatar: str = ""

    @staticmethod
    def from_json(d: Dict[str, Any], default_stats: Stats, default_skill: Skill, role_color: str = "#6b7280") -> "Unit":
        return Unit(
            id=d["id"],
            name=d["name"],
            cost=int(d["cost"]),
            factions=list(d.get("factions", [])),
            classes=list(d.get("classes", [])),
            stats=default_stats,
            skill=default_skill,
            role=d.get("role", ""),
            role_color=role_color,
            avatar=d.get("avatar", ""),
        )
