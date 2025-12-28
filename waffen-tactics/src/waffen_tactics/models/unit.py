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
    mana_cost: int = 0
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
    last_attack_time: float = 0.0

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
            last_attack_time=0.0,
        )


# Combat domain models - immutable where possible

@dataclass(frozen=True)
class CombatUnitStats:
    """Immutable combat unit statistics"""
    hp: int
    attack: int
    defense: int
    attack_speed: float
    max_mana: int
    mana_regen: int = 0
    star_level: int = 1
    position: str = 'front'  # 'front' or 'back'
    mana_on_attack: int = 10


@dataclass(frozen=True)
class CombatUnitSkill:
    """Immutable combat skill definition"""
    name: str
    description: str
    effect: Dict[str, Any]


@dataclass
class CombatUnitState:
    """Mutable combat unit state"""
    current_hp: int
    current_mana: int
    shield: int = 0
    effects: List[Dict[str, Any]] = field(default_factory=list)
    last_attack_time: float = 0.0
    kills: int = 0
    stolen_defense: int = 0
    collected_stats: Dict[str, float] = field(default_factory=dict)
    hp_regen_accumulator: float = 0.0

    def copy(self) -> 'CombatUnitState':
        """Create a copy of the state"""
        return CombatUnitState(
            current_hp=self.current_hp,
            current_mana=self.current_mana,
            shield=self.shield,
            effects=self.effects.copy(),
            last_attack_time=self.last_attack_time,
            kills=self.kills,
            stolen_defense=self.stolen_defense,
            collected_stats=self.collected_stats.copy(),
            hp_regen_accumulator=self.hp_regen_accumulator
        )


# Computed stats cache - computed from effects
@dataclass
class ComputedStats:
    """Computed passive values from effects"""
    lifesteal: float = 0.0
    damage_reduction: float = 0.0
    hp_regen_per_sec: float = 0.0

    @staticmethod
    def from_effects(effects: List[Dict[str, Any]]) -> 'ComputedStats':
        """Compute stats from effects list"""
        lifesteal = 0.0
        damage_reduction = 0.0
        hp_regen_per_sec = 0.0

        for eff in effects:
            etype = eff.get('type')
            if etype == 'lifesteal':
                lifesteal = max(lifesteal, float(eff.get('value', 0)))
            elif etype == 'damage_reduction':
                damage_reduction = max(damage_reduction, float(eff.get('value', 0)))
            elif etype == 'hp_regen_on_kill':
                hp_regen_per_sec += float(eff.get('value', 0))

        return ComputedStats(
            lifesteal=lifesteal,
            damage_reduction=damage_reduction,
            hp_regen_per_sec=hp_regen_per_sec
        )
