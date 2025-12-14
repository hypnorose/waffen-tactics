"""
Combat win conditions processor - handles win condition checking and combat finishing
"""
from typing import List, Dict, Any, Optional
from typing import List, Dict, Any


class CombatWinConditionsProcessor:
    """Handles win condition checking and combat result formatting"""

    def _check_win_conditions(self, a_hp: List[int], b_hp: List[int]) -> Optional[str]:
        """Check if either team has won. Returns winner or None."""
        if all(h <= 0 for h in b_hp):
            return "team_a"
        if all(h <= 0 for h in a_hp):
            return "team_b"
        return None

    def _finish_combat(
        self,
        winner: str,
        time: float,
        a_hp: List[int],
        b_hp: List[int],
        log: List[str]
    ) -> Dict[str, Any]:
        """Format and return combat result."""
        return {
            'winner': winner,
            'duration': time,
            'team_a_survivors': sum(1 for h in a_hp if h > 0),
            'team_b_survivors': sum(1 for h in b_hp if h > 0),
            'log': log
        }