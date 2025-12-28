from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum


class TargetType(Enum):
    """Types of targets for skill effects"""
    SELF = "self"
    SINGLE_ENEMY = "single_enemy"
    SINGLE_ENEMY_PERSISTENT = "single_enemy_persistent"
    ENEMY_TEAM = "enemy_team"
    ENEMY_FRONT = "enemy_front"
    ALLY_TEAM = "ally_team"
    ALLY_FRONT = "ally_front"


class EffectType(Enum):
    """Types of skill effects"""
    DAMAGE = "damage"
    HEAL = "heal"
    SHIELD = "shield"
    BUFF = "buff"
    DEBUFF = "debuff"
    STUN = "stun"
    DELAY = "delay"
    REPEAT = "repeat"
    CONDITIONAL = "conditional"
    DAMAGE_OVER_TIME = "damage_over_time"


@dataclass
class Effect:
    """Represents a single effect in a skill"""
    type: EffectType
    target: TargetType = TargetType.SELF
    # Effect-specific parameters
    params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate effect after initialization"""
        if isinstance(self.type, str):
            self.type = EffectType(self.type)
        if isinstance(self.target, str):
            self.target = TargetType(self.target)


@dataclass
class Skill:
    """Represents a unit's skill"""
    name: str
    description: str
    mana_cost: int | None = None
    effects: List[Effect] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Skill':
        """Create Skill from dictionary (JSON)"""
        effects = []
        for effect_data in data.get('effects', []):
            effects.append(Effect(
                type=effect_data['type'],
                target=effect_data.get('target', 'self'),
                params=effect_data
            ))

        return cls(
            name=data['name'],
            description=data.get('description', ''),
            mana_cost=data.get('mana_cost'),
            effects=effects
        )


@dataclass
class SkillExecutionContext:
    """Context for executing a skill"""
    caster: Any  # CombatUnit
    team_a: List[Any]  # List[CombatUnit]
    team_b: List[Any]  # List[CombatUnit]
    combat_time: float = 0.0
    random_seed: Optional[int] = None
    persistent_target: Optional[Any] = None  # For SINGLE_ENEMY_PERSISTENT targeting
    # Optional event callback from simulator so effect handlers can emit canonical events
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None

    @property
    def caster_team(self) -> List[Any]:
        """Get the caster's team"""
        return self.team_a if any(u.id == self.caster.id for u in self.team_a) else self.team_b

    @property
    def enemy_team(self) -> List[Any]:
        """Get the enemy team"""
        return self.team_b if any(u.id == self.caster.id for u in self.team_a) else self.team_a
