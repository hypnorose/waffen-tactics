"""
Combat win conditions processor - handles win condition checking and combat finishing
"""
from typing import List, Dict, Any, Optional


class CombatWinConditionsProcessor:
    """Handles win condition checking and combat result formatting"""

    def _check_win_conditions(self, a_hp: List[int], b_hp: List[int]) -> Optional[str]:
        """Check if either team has won. Returns winner or None."""
        if all(h <= 0 for h in b_hp):
            return "team_a"
        if all(h <= 0 for h in a_hp):
            return "team_b"
        return None