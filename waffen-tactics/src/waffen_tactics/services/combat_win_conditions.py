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

    def _finish_combat(
        self,
        winner: str,
        duration: float,
        a_hp: List[int],
        b_hp: List[int],
        log: List[str],
        winning_team: List['CombatUnit']
    ) -> Dict[str, Any]:
        """Format and return combat result."""
        # Count survivors
        survivors_a = sum(1 for hp in a_hp if hp > 0)
        survivors_b = sum(1 for hp in b_hp if hp > 0)
        
        return {
            "winner": winner,
            "duration": duration,
            "survivors_a": survivors_a,
            "survivors_b": survivors_b,
            "log": log,
            "final_hp_a": a_hp.copy(),
            "final_hp_b": b_hp.copy(),
        }