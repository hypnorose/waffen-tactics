"""
Stat Buff Handlers - Individual handlers for different stat types
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .combat_unit import CombatUnit

from .stat_calculator import StatCalculator


class StatBuffHandler(ABC):
    """Abstract base class for stat buff handlers"""

    def __init__(self, stat_name: str):
        self.stat_name = stat_name

    @abstractmethod
    def apply_buff(
        self,
        unit: 'CombatUnit',
        value: float,
        is_percentage: bool,
        amplifier: float,
        hp_list: List[int],
        unit_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ) -> None:
        """Apply buff to the specific stat"""
        pass

    @abstractmethod
    def get_base_value(self, unit: 'CombatUnit') -> float:
        """Get the base value of this stat from the unit"""
        pass

    @abstractmethod
    def set_value(self, unit: 'CombatUnit', value: float) -> None:
        """Set the value of this stat on the unit"""
        pass


class AttackBuffHandler(StatBuffHandler):
    """Handler for attack stat buffs"""

    def __init__(self):
        super().__init__('attack')

    def get_base_value(self, unit: 'CombatUnit') -> float:
        return unit.attack

    def set_value(self, unit: 'CombatUnit', value: float) -> None:
        unit.attack = StatCalculator.validate_stat_value(value, 'attack')

    def apply_buff(
        self,
        unit: 'CombatUnit',
        value: float,
        is_percentage: bool,
        amplifier: float,
        hp_list: List[int],
        unit_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ) -> None:
        base_value = self.get_base_value(unit)
        buffed_value = StatCalculator.calculate_buff(base_value, value, is_percentage, amplifier)
        final_value = base_value + buffed_value

        self.set_value(unit, final_value)
        log.append(f"{unit.name} gains +{buffed_value:.0f} Atak (stat_buff)")

        if event_callback:
            event_callback('stat_buff', {
                'unit_id': unit.id,
                'unit_name': unit.name,
                'stat': 'attack',
                'amount': buffed_value,
                'side': side,
                'timestamp': time,
                'cause': 'effect'
            })


class DefenseBuffHandler(StatBuffHandler):
    """Handler for defense stat buffs"""

    def __init__(self):
        super().__init__('defense')

    def get_base_value(self, unit: 'CombatUnit') -> float:
        return unit.defense

    def set_value(self, unit: 'CombatUnit', value: float) -> None:
        unit.defense = StatCalculator.validate_stat_value(value, 'defense')

    def apply_buff(
        self,
        unit: 'CombatUnit',
        value: float,
        is_percentage: bool,
        amplifier: float,
        hp_list: List[int],
        unit_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ) -> None:
        base_value = self.get_base_value(unit)
        buffed_value = StatCalculator.calculate_buff(base_value, value, is_percentage, amplifier)
        final_value = base_value + buffed_value

        self.set_value(unit, final_value)
        log.append(f"{unit.name} gains +{buffed_value:.0f} {self.stat_name.capitalize()} (stat_buff)")

        if event_callback:
            event_callback('stat_buff', {
                'unit_id': unit.id,
                'unit_name': unit.name,
                'stat': self.stat_name,
                'amount': buffed_value,
                'side': side,
                'timestamp': time,
                'cause': 'effect'
            })


class HpBuffHandler(StatBuffHandler):
    """Handler for HP stat buffs"""

    def __init__(self):
        super().__init__('hp')

    def get_base_value(self, unit: 'CombatUnit') -> float:
        return unit.hp

    def set_value(self, unit: 'CombatUnit', value: float) -> None:
        unit.hp = StatCalculator.validate_stat_value(value, 'hp')

    def apply_buff(
        self,
        unit: 'CombatUnit',
        value: float,
        is_percentage: bool,
        amplifier: float,
        hp_list: List[int],
        unit_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ) -> None:
        base_value = self.get_base_value(unit)
        buffed_value = StatCalculator.calculate_buff(base_value, value, is_percentage, amplifier)
        final_value = base_value + buffed_value

        self.set_value(unit, final_value)
        log.append(f"{unit.name} gains +{buffed_value:.0f} HP (stat_buff)")

        if event_callback:
            event_callback('stat_buff', {
                'unit_id': unit.id,
                'unit_name': unit.name,
                'stat': 'hp',
                'amount': buffed_value,
                'side': side,
                'timestamp': time,
                'cause': 'effect'
            })


class AttackSpeedBuffHandler(StatBuffHandler):
    """Handler for attack speed stat buffs"""

    def __init__(self):
        super().__init__('attack_speed')

    def get_base_value(self, unit: 'CombatUnit') -> float:
        return unit.attack_speed

    def set_value(self, unit: 'CombatUnit', value: float) -> None:
        unit.attack_speed = StatCalculator.validate_stat_value(value, 'attack_speed')

    def apply_buff(
        self,
        unit: 'CombatUnit',
        value: float,
        is_percentage: bool,
        amplifier: float,
        hp_list: List[int],
        unit_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ) -> None:
        base_value = self.get_base_value(unit)
        buffed_value = StatCalculator.calculate_buff(base_value, value, is_percentage, amplifier)
        final_value = base_value + buffed_value

        self.set_value(unit, final_value)
        log.append(f"{unit.name} gains +{buffed_value:.2f} Attack Speed (stat_buff)")

        if event_callback:
            event_callback('stat_buff', {
                'unit_id': unit.id,
                'unit_name': unit.name,
                'stat': 'attack_speed',
                'amount': buffed_value,
                'side': side,
                'timestamp': time,
                'cause': 'effect'
            })


class ManaRegenBuffHandler(StatBuffHandler):
    """Handler for mana regen stat buffs"""

    def __init__(self):
        super().__init__('mana_regen')

    def get_base_value(self, unit: 'CombatUnit') -> float:
        return unit.mana_regen

    def set_value(self, unit: 'CombatUnit', value: float) -> None:
        unit.mana_regen = StatCalculator.validate_stat_value(value, 'mana_regen')

    def apply_buff(
        self,
        unit: 'CombatUnit',
        value: float,
        is_percentage: bool,
        amplifier: float,
        hp_list: List[int],
        unit_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ) -> None:
        base_value = self.get_base_value(unit)
        buffed_value = StatCalculator.calculate_buff(base_value, value, is_percentage, amplifier)
        final_value = base_value + buffed_value

        self.set_value(unit, final_value)
        log.append(f"{unit.name} gains +{buffed_value:.0f} Mana Regen (stat_buff)")

        if event_callback:
            event_callback('stat_buff', {
                'unit_id': unit.id,
                'unit_name': unit.name,
                'stat': self.stat_name,
                'amount': buffed_value,
                'side': side,
                'timestamp': time,
                'cause': 'effect'
            })


class LifestealBuffHandler(StatBuffHandler):
    """Handler for lifesteal stat buffs"""

    def __init__(self):
        super().__init__('lifesteal')

    def get_base_value(self, unit: 'CombatUnit') -> float:
        return unit.lifesteal

    def set_value(self, unit: 'CombatUnit', value: float) -> None:
        unit.lifesteal = value  # Allow negative for debuffs

    def apply_buff(
        self,
        unit: 'CombatUnit',
        value: float,
        is_percentage: bool,
        amplifier: float,
        hp_list: List[int],
        unit_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ) -> None:
        # Lifesteal is typically a percentage, convert to decimal
        lifesteal_gain = value / 100.0 if is_percentage else value
        final_value = self.get_base_value(unit) + lifesteal_gain

        self.set_value(unit, final_value)
        log.append(f"{unit.name} gains +{lifesteal_gain:.1%} Lifesteal (stat_buff)")

        if event_callback:
            event_callback('stat_buff', {
                'unit_id': unit.id,
                'unit_name': unit.name,
                'stat': 'lifesteal',
                'amount': lifesteal_gain,
                'side': side,
                'timestamp': time,
                'cause': 'effect'
            })


class DamageReductionBuffHandler(StatBuffHandler):
    """Handler for damage reduction stat buffs"""

    def __init__(self):
        super().__init__('damage_reduction')

    def get_base_value(self, unit: 'CombatUnit') -> float:
        return unit.damage_reduction

    def set_value(self, unit: 'CombatUnit', value: float) -> None:
        unit.damage_reduction = value  # Allow negative

    def apply_buff(
        self,
        unit: 'CombatUnit',
        value: float,
        is_percentage: bool,
        amplifier: float,
        hp_list: List[int],
        unit_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ) -> None:
        # Damage reduction is typically a percentage, convert to decimal
        reduction_gain = value / 100.0 if is_percentage else value
        final_value = self.get_base_value(unit) + reduction_gain

        self.set_value(unit, final_value)
        log.append(f"{unit.name} gains +{reduction_gain:.1%} Damage Reduction (stat_buff)")

        if event_callback:
            event_callback('stat_buff', {
                'unit_id': unit.id,
                'unit_name': unit.name,
                'stat': 'damage_reduction',
                'amount': reduction_gain,
                'side': side,
                'timestamp': time,
                'cause': 'effect'
            })


class HpRegenPerSecBuffHandler(StatBuffHandler):
    """Handler for HP regen per second stat buffs"""

    def __init__(self):
        super().__init__('hp_regen_per_sec')

    def get_base_value(self, unit: 'CombatUnit') -> float:
        return unit.hp_regen_per_sec

    def set_value(self, unit: 'CombatUnit', value: float) -> None:
        unit.hp_regen_per_sec = value

    def apply_buff(
        self,
        unit: 'CombatUnit',
        value: float,
        is_percentage: bool,
        amplifier: float,
        hp_list: List[int],
        unit_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ) -> None:
        base_value = self.get_base_value(unit)
        regen_gain = StatCalculator.calculate_buff(base_value, value, is_percentage, amplifier)
        final_value = base_value + regen_gain

        self.set_value(unit, final_value)
        log.append(f"{unit.name} gains +{regen_gain:.2f} HP Regen/sec (stat_buff)")

        if event_callback:
            event_callback('regen_gain', {
                'unit_id': unit.id,
                'unit_name': unit.name,
                'amount_per_sec': regen_gain,
                'side': side,
                'timestamp': time
            })


# Registry of stat handlers
