"""
Stat Calculator - Utility for calculating stat buffs and modifications
"""
from typing import Dict, Any


class StatCalculator:
    """Utility class for stat calculations following DRY principles"""

    @staticmethod
    def calculate_buff(base_value: float, buff_value: float, is_percentage: bool, amplifier: float = 1.0) -> float:
        """
        Calculate buffed value for a stat.

        Args:
            base_value: The base stat value
            buff_value: The buff amount
            is_percentage: Whether buff_value is a percentage
            amplifier: Additional multiplier (e.g., from buff amplifiers)

        Returns:
            The final buffed value
        """
        if is_percentage:
            return base_value * (buff_value / 100.0) * amplifier
        return buff_value * amplifier
    @staticmethod
    def calculate_buff_increment(base_increment: float, buff_value: float, buff_type: str, base_stat_value: float = None) -> float:
        """
        Calculate the base increment for a buff before applying amplifiers.

        Args:
            base_increment: Base increment value (usually 0)
            buff_value: The buff amount
            buff_type: Type of buff ('flat' or 'percentage')
            base_stat_value: Base stat value for percentage calculations

        Returns:
            The calculated buff increment
        """
        if buff_type == 'percentage':
            if base_stat_value is None:
                return 0
            return base_stat_value * (buff_value / 100.0)
        elif buff_type == 'flat':
            return buff_value
        else:
            raise ValueError(f"Unknown buff_type: {buff_type}")

    @staticmethod
    def calculate_percentage_buff(base_value: float, percentage: float, amplifier: float = 1.0) -> float:
        """
        Calculate percentage buff on a base value.

        Args:
            base_value: The base stat value
            percentage: Percentage to buff (e.g., 10 for +10%)
            amplifier: Additional multiplier

        Returns:
            The buffed value
        """
        return base_value * (1.0 + (percentage / 100.0) * amplifier)

    @staticmethod
    def get_buff_amplifier(unit_effects: list) -> float:
        """
        Calculate total buff amplifier from unit effects.

        Args:
            unit_effects: List of effect dictionaries

        Returns:
            Total amplifier multiplier
        """
        amplifier = 1.0
        for eff in unit_effects:
            if eff.get('type') == 'buff_amplifier':
                amplifier *= float(eff.get('multiplier', 1.0))
        return amplifier

    @staticmethod
    def validate_stat_value(value: float, stat_name: str) -> float:
        """
        Validate and clamp stat values to reasonable ranges.

        Args:
            value: The stat value to validate
            stat_name: Name of the stat for logging

        Returns:
            Validated stat value
        """
        # Prevent negative values for most stats
        if stat_name in ('attack', 'defense', 'hp', 'max_hp', 'attack_speed', 'mana_regen'):
            return max(0, value)

        # Allow negative for debuffs like damage_reduction
        return value
