"""
CombatState class - encapsulates authoritative combat state management
"""
from typing import List, Dict, Any, Tuple
import logging


class CombatState:
    """Encapsulates the authoritative state for combat simulation.

    Manages both unit objects and HP lists as a single source of truth,
    eliminating ad-hoc synchronization logic while preserving emitter-based
    change notifications.
    """

    def __init__(self, team_a: List['CombatUnit'], team_b: List['CombatUnit']):
        """Initialize combat state with teams.

        Args:
            team_a: First team units
            team_b: Second team units
        """
        self.team_a = team_a
        self.team_b = team_b

        # Initialize HP lists from unit current HP
        self.a_hp = [u.hp for u in team_a]
        self.b_hp = [u.hp for u in team_b]
        # Initialize authoritative mana lists from unit current mana
        try:
            self.a_mana = [int(getattr(u, 'mana', 0)) for u in team_a]
            self.b_mana = [int(getattr(u, 'mana', 0)) for u in team_b]
        except Exception:
            self.a_mana = [0 for _ in team_a]
            self.b_mana = [0 for _ in team_b]

    @property
    def mana_arrays(self) -> Dict[str, List[int]]:
        return {'team_a': self.a_mana, 'team_b': self.b_mana}

    def sync_mana_lists_from_units(self) -> None:
        """Sync mana lists to match current unit.mana values.

        This should be called before generating snapshots to ensure mana
        mirrors reflect any changes made to units through emitters.
        """
        for i, u in enumerate(self.team_a):
            try:
                new_m = max(0, int(getattr(u, 'mana', self.a_mana[i])))
            except Exception:
                new_m = self.a_mana[i]
            self.a_mana[i] = new_m

        for i, u in enumerate(self.team_b):
            try:
                new_m = max(0, int(getattr(u, 'mana', self.b_mana[i])))
            except Exception:
                new_m = self.b_mana[i]
            self.b_mana[i] = new_m

    def sync_hp_lists_from_units(self) -> None:
        """Sync HP lists to match current unit.hp values.

        This should be called before snapshot generation to ensure
        HP lists reflect any changes made to units through emitters.
        """
        for i, u in enumerate(self.team_a):
            new_hp = max(0, int(getattr(u, 'hp', self.a_hp[i])))
            if getattr(u, 'id', None) == 'mrozu' and new_hp != self.a_hp[i]:
                print(f"[COMBAT_STATE SYNC] mrozu a_hp[{i}]: {self.a_hp[i]} -> {new_hp} (unit.hp={u.hp})")
            self.a_hp[i] = new_hp

        for i, u in enumerate(self.team_b):
            new_hp = max(0, int(getattr(u, 'hp', self.b_hp[i])))
            if getattr(u, 'id', None) == 'mrozu' and new_hp != self.b_hp[i]:
                print(f"[COMBAT_STATE SYNC] mrozu b_hp[{i}]: {self.b_hp[i]} -> {new_hp} (unit.hp={u.hp})")
            self.b_hp[i] = new_hp

    def get_snapshot_data(self, timestamp: float) -> Dict[str, Any]:
        """Generate snapshot data for state_snapshot event.

        Returns:
            Dict containing player_units and opponent_units with current state
        """
        # Ensure HP lists are synced before generating snapshot
        self.sync_hp_lists_from_units()
        # Ensure mana lists are synced as well
        try:
            self.sync_mana_lists_from_units()
        except Exception:
            pass
        return {
            'player_units': [u.to_dict(self.a_hp[i], current_mana=self.a_mana[i]) for i, u in enumerate(self.team_a)],
            'opponent_units': [u.to_dict(self.b_hp[i], current_mana=self.b_mana[i]) for i, u in enumerate(self.team_b)],
            'timestamp': timestamp
        }

    def get_hp_for_unit(self, unit_id: str) -> int:
        """Get current HP for a unit by ID.

        Args:
            unit_id: The unit ID to look up

        Returns:
            Current HP value, or 0 if unit not found
        """
        for i, u in enumerate(self.team_a):
            if u.id == unit_id:
                return self.a_hp[i]
        for i, u in enumerate(self.team_b):
            if u.id == unit_id:
                return self.b_hp[i]
        return 0

    def get_unit_and_hp_index(self, unit_id: str) -> Tuple['CombatUnit', int, bool]:
        """Get unit, HP list index, and team flag for a unit ID.

        Args:
            unit_id: The unit ID to look up

        Returns:
            Tuple of (unit, hp_index, is_team_a)
        """
        for i, u in enumerate(self.team_a):
            if u.id == unit_id:
                return u, i, True
        for i, u in enumerate(self.team_b):
            if u.id == unit_id:
                return u, i, False
        raise ValueError(f"Unit {unit_id} not found in combat state")

    def check_win_conditions(self) -> str:
        """Check if either team has won.

        Returns:
            "team_a", "team_b", or None if no winner yet
        """
        a_alive = sum(1 for h in self.a_hp if h > 0)
        b_alive = sum(1 for h in self.b_hp if h > 0)

        if a_alive > 0 and b_alive == 0:
            return "team_a"
        elif b_alive > 0 and a_alive == 0:
            return "team_b"

        return None

    def get_winner_by_total_hp(self) -> str:
        """Determine winner by total HP when timeout occurs.

        Returns:
            "team_a" or "team_b"
        """
        sum_a = sum(max(0, h) for h in self.a_hp)
        sum_b = sum(max(0, h) for h in self.b_hp)
        return "team_a" if sum_a >= sum_b else "team_b"

    def get_combat_result(self, winner: str, duration: float, winning_team: List['CombatUnit'], log: List[str]) -> Dict[str, Any]:
        """Generate combat result dict.

        Args:
            winner: Winning team ("team_a" or "team_b")
            duration: Combat duration in seconds
            winning_team: The winning team units
            log: Combat log entries

        Returns:
            Dict with combat result data
        """
        # Calculate star sum of surviving units from winning team
        surviving_star_sum = 0
        hp_list = self.a_hp if winning_team == self.team_a else self.b_hp

        for i, unit in enumerate(winning_team):
            if hp_list[i] > 0:
                surviving_star_sum += getattr(unit, 'star_level', 1)

        return {
            'winner': winner,
            'duration': duration,
            'team_a_survivors': sum(1 for h in self.a_hp if h > 0),
            'team_b_survivors': sum(1 for h in self.b_hp if h > 0),
            'surviving_star_sum': surviving_star_sum,
            'log': log
        }

    def get_debug_hp_string(self) -> str:
        """Get debug string showing current HP state.

        Returns:
            Formatted string with team HP lists
        """
        return f"a_hp={self.a_hp}, b_hp={self.b_hp}"

    def validate_state_consistency(self) -> List[str]:
        """Validate that unit HP and HP lists are consistent.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        for i, u in enumerate(self.team_a):
            if u.hp != self.a_hp[i]:
                errors.append(f"Team A unit {u.id}: unit.hp={u.hp} != a_hp[{i}]={self.a_hp[i]}")

        for i, u in enumerate(self.team_b):
            if u.hp != self.b_hp[i]:
                errors.append(f"Team B unit {u.id}: unit.hp={u.hp} != b_hp[{i}]={self.b_hp[i]}")

        return errors