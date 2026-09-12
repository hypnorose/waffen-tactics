"""
Recipient Resolver - Handles finding buff recipients based on target type
"""
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .combat_unit import CombatUnit


class RecipientResolutionError(ValueError):
    """Base error for an invalid or incomplete stat-buff recipient request."""


class UnsupportedRecipientTargetError(RecipientResolutionError):
    """Raised when a stat-buff target is outside the shared runtime contract."""


class IncompleteRecipientContextError(RecipientResolutionError):
    """Raised when a legal target is missing authoritative team context."""


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
        if target == 'self':
            recipients = [source_unit]
        elif target == 'team':
            if side == 'team_a':
                if attacking_team is None:
                    raise IncompleteRecipientContextError(
                        "team target requires attacking_team for side team_a"
                    )
                recipients = [u for u in attacking_team if getattr(u, 'hp', 0) > 0]
            elif side == 'team_b':
                if defending_team is None:
                    raise IncompleteRecipientContextError(
                        "team target requires defending_team for side team_b"
                    )
                recipients = [u for u in defending_team if getattr(u, 'hp', 0) > 0]
            else:
                raise IncompleteRecipientContextError(
                    f"team target requires side team_a or team_b, got {side!r}"
                )
        elif target == 'board':
            if attacking_team is None or defending_team is None:
                raise IncompleteRecipientContextError(
                    "board target requires both attacking_team and defending_team"
                )
            # Preserve the authoritative simulator order: attacking side first,
            # then defending side. Explicit empty lists are valid no-recipient
            # contexts and must not silently become a self-target.
            recipients = [
                *[u for u in attacking_team if getattr(u, 'hp', 0) > 0],
                *[u for u in defending_team if getattr(u, 'hp', 0) > 0],
            ]
        else:
            raise UnsupportedRecipientTargetError(
                f"Unsupported stat-buff recipient target: {target!r}"
            )

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
