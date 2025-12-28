from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, TypedDict, Optional, Union
import uuid


@dataclass(frozen=True)
class UnitState:
    id: str
    name: str
    hp: int
    max_hp: int
    shield: int = 0
    mana: int = 0
    max_mana: int = 0
    attack: int = 10
    defense: int = 0
    attack_speed: float = 1.0
    position: Literal['front', 'back'] = 'front'


@dataclass(frozen=True)
class CombatSnapshot:
    timestamp: float
    player: List[UnitState]
    opponent: List[UnitState]
    seq: int


@dataclass(frozen=True)
class UnitAttackEvent:
    type: Literal['unit_attack'] = 'unit_attack'
    seq: int = 0
    event_id: str = ''
    timestamp: float = 0.0
    attacker_id: str = ''
    attacker_name: str = ''
    target_id: str = ''
    target_name: str = ''
    damage: int = 0
    applied_damage: int = 0
    target_hp: int = 0
    new_hp: int = 0
    cause: str = 'attack'
    is_skill: bool = False


Event = Union[UnitAttackEvent]


def make_event_id() -> str:
    return str(uuid.uuid4())
