from dataclasses import dataclass, field
from typing import List, Dict
from .unit import Unit

@dataclass
class PlayerProfile:
    nickname: str
    level: int = 1
    xp: int = 0
    gold: int = 0
    wins: int = 0
    rounds: int = 0

@dataclass
class TeamSnapshot:
    owner_nickname: str
    units: List[Unit] = field(default_factory=list)
    synergies: Dict[str, int] = field(default_factory=dict)
    level: int = 1
    wins: int = 0
    rounds: int = 0
