"""
Stat Buff Handlers - Individual handlers for different stat types
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .combat_unit import CombatUnit

from .stat_calculator import StatCalculator
from .event_canonicalizer import emit_stat_buff, emit_regen_gain


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

        # Apply via canonical emitter when possible so the mutation is centralized
        added = buffed_value
        log.append(f"{unit.name} gains +{buffed_value:.0f} Atak (stat_buff)")
        if event_callback:
            # emit canonical stat_buff without noisy debug prints
            emit_stat_buff(event_callback, unit, 'attack', added, value_type='flat', duration=None, permanent=False, source=None, side=side, timestamp=time, cause='effect')
        else:
            self.set_value(unit, final_value)


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

        added = buffed_value
        log.append(f"{unit.name} gains +{buffed_value:.0f} {self.stat_name.capitalize()} (stat_buff)")
        if event_callback:
            # emit canonical stat_buff without noisy debug prints
            emit_stat_buff(event_callback, unit, self.stat_name, added, value_type='flat', duration=None, permanent=False, source=None, side=side, timestamp=time, cause='effect')
        else:
            self.set_value(unit, final_value)


class HpBuffHandler(StatBuffHandler):
    """Handler for HP stat buffs"""

    def __init__(self):
        super().__init__('hp')

    def get_base_value(self, unit: 'CombatUnit') -> float:
        return unit.hp

    def set_value(self, unit: 'CombatUnit', value: float) -> None:
        # Route through central setter for consistency
        validated = StatCalculator.validate_stat_value(value, 'hp')
        # Route absolute HP changes through canonical emitters instead of
        # bypassing the guard with `caller_module` strings. Compute the
        # delta from the current HP and apply via `emit_heal`/`emit_damage`.
        try:
            cur = int(getattr(unit, 'hp', 0))
        except Exception:
            cur = 0
        delta = int(validated) - cur
        from waffen_tactics.services.event_canonicalizer import emit_heal, emit_damage

        if delta > 0:
            emit_heal(None, unit, delta, source=None, side=None)
        elif delta < 0:
            emit_damage(None, None, unit, raw_damage=abs(delta), emit_event=False)

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

        added = buffed_value
        log.append(f"{unit.name} gains +{buffed_value:.0f} HP (stat_buff)")
        # Always route HP changes through the canonical stat/HP emitters.
        # `emit_stat_buff` will apply HP changes (via emit_heal) even when
        # `event_callback` is None (dry-run), ensuring a single authoritative
        # path for HP mutation.
        emit_stat_buff(event_callback, unit, 'hp', added, value_type='flat', duration=None, permanent=False, source=None, side=side, timestamp=time, cause='effect')
        # Sync hp_list with unit's updated HP (emitter will keep unit.hp authoritative)
        try:
            hp_list[unit_idx] = unit.hp
        except Exception:
            pass


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

        added = buffed_value
        log.append(f"{unit.name} gains +{buffed_value:.2f} Attack Speed (stat_buff)")
        if event_callback:
            emit_stat_buff(event_callback, unit, 'attack_speed', added, value_type='flat', duration=None, permanent=False, source=None, side=side, timestamp=time, cause='effect')
        else:
            self.set_value(unit, final_value)


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

        added = buffed_value
        log.append(f"{unit.name} gains +{buffed_value:.0f} Mana Regen (stat_buff)")
        if event_callback:
            emit_stat_buff(event_callback, unit, self.stat_name, added, value_type='flat', duration=None, permanent=False, source=None, side=side, timestamp=time, cause='effect')
        else:
            self.set_value(unit, final_value)


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

        added = lifesteal_gain
        log.append(f"{unit.name} gains +{lifesteal_gain:.1%} Lifesteal (stat_buff)")
        if event_callback:
            emit_stat_buff(event_callback, unit, 'lifesteal', added, value_type='flat', duration=None, permanent=False, source=None, side=side, timestamp=time, cause='effect')
        else:
            self.set_value(unit, final_value)


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

        added = reduction_gain
        log.append(f"{unit.name} gains +{reduction_gain:.1%} Damage Reduction (stat_buff)")
        if event_callback:
            emit_stat_buff(event_callback, unit, 'damage_reduction', added, value_type='flat', duration=None, permanent=False, source=None, side=side, timestamp=time, cause='effect')
        else:
            self.set_value(unit, final_value)


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

        added = regen_gain
        log.append(f"{unit.name} gains +{regen_gain:.2f} HP Regen/sec (stat_buff)")
        if event_callback:
            emit_regen_gain(event_callback, unit, added, side=side, timestamp=time)
        else:
            self.set_value(unit, final_value)


# Registry of stat handlers
