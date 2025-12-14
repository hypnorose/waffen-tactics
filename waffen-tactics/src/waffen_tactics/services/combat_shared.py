"""
Shared combat logic for both Discord bot and web version
"""
from .combat_unit import CombatUnit
from .combat_simulator import CombatSimulator

__all__ = ['CombatUnit', 'CombatSimulator']
