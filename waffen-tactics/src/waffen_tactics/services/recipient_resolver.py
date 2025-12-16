"""
Recipient Resolver - Handles finding buff recipients based on target type
"""
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .combat_unit import CombatUnit


class RecipientResolver:
    """Handles finding buff recipients based on effect target configuration"""

    @staticmethod
    def find_recipients(
        source_unit: 'CombatUnit',
        target: str,
        only_same_trait: bool,
        attacking_team: Optional[List['CombatUnit']] = None,
        defending_team: Optional[List['CombatUnit']] = None,
        side: str = ""
    ) -> List['CombatUnit']:
        """
        Find recipients for a buff based on target configuration.

        Args:
            source_unit: The unit applying the buff
            target: Target type ('self', 'team', 'board')
            only_same_trait: Whether to filter to units with same traits
            attacking_team: The attacking team units
            defending_team: The defending team units
            side: Which side the effect is happening on ('team_a' or 'team_b')

        Returns:
            List of recipient units
        """
        recipients = []

        if target == 'self':
            recipients = [source_unit]
        elif target == 'team':
            # Choose team based on side
            if side == 'team_a' and attacking_team:
                recipients = [u for u in attacking_team if getattr(u, 'hp', 0) > 0]
            elif side == 'team_b' and defending_team:
                recipients = [u for u in defending_team if getattr(u, 'hp', 0) > 0]
        elif target == 'board':
            # All units on the board
            if attacking_team:
                recipients.extend([u for u in attacking_team if getattr(u, 'hp', 0) > 0])
            if defending_team:
                recipients.extend([u for u in defending_team if getattr(u, 'hp', 0) > 0])
            # If no teams provided, fallback to self
            if not attacking_team and not defending_team:
                recipients = [source_unit]
        else:
            # Unknown target, fallback to self
            recipients = [source_unit]

        # Filter by same trait if requested
        if only_same_trait:
            source_traits = set(getattr(source_unit, 'factions', []) + getattr(source_unit, 'classes', []))
            recipients = [
                r for r in recipients
                if source_traits.intersection(set(getattr(r, 'factions', []) + getattr(r, 'classes', [])))
            ]

        return recipients

    @staticmethod
    def get_hp_list_for_unit(
        unit: 'CombatUnit',
        attacking_team: Optional[List['CombatUnit']] = None,
        defending_team: Optional[List['CombatUnit']] = None,
        attacking_hp: Optional[List[int]] = None,
        defending_hp: Optional[List[int]] = None
    ) -> Optional[List[int]]:
        """
        Get the HP list for a unit's team.

        Args:
            unit: The unit to find HP list for
            attacking_team: Attacking team units
            defending_team: Defending team units
            attacking_hp: Attacking team HP values
            defending_hp: Defending team HP values

        Returns:
            The appropriate HP list or None
        """
        if attacking_team and unit in attacking_team and attacking_hp:
            return attacking_hp
        elif defending_team and unit in defending_team and defending_hp:
            return defending_hp
        return None

    @staticmethod
    def get_unit_index(
        unit: 'CombatUnit',
        team: Optional[List['CombatUnit']] = None
    ) -> int:
        """
        Get the index of a unit in its team.

        Args:
            unit: The unit to find
            team: The team list

        Returns:
            Index of the unit or -1 if not found
        """
        if team and unit in team:
            return team.index(unit)
        return -1

