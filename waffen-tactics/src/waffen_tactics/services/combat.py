"""
Wrapper for shared combat logic - maintains API compatibility with existing code
"""
from typing import List, Dict
from waffen_tactics.models.unit import Unit
from waffen_tactics.services.combat_shared import CombatSimulator as SharedCombatSimulator, CombatUnit


class CombatSimulator:
    """Wrapper that adapts Unit objects to shared combat system"""
    
    def __init__(self):
        self.shared_sim = SharedCombatSimulator(dt=0.1, timeout=120)
    
    def simulate(self, team_a: List[Unit], team_b: List[Unit], timeout: int = 120, event_callback=None, round_number: int = 1) -> Dict[str, any]:
        """
        Simulate combat using shared logic
        
        Converts Unit objects to CombatUnit and delegates to shared simulator
        """
        # Convert to CombatUnit
        team_a_combat = [
            CombatUnit(
                id=f"a_{i}",
                name=u.name,
                hp=u.stats.hp,
                attack=u.stats.attack,
                defense=u.stats.defense,
                attack_speed=u.stats.attack_speed,
                position='front',
                max_mana=u.stats.max_mana,
                skill=u.skill,
                stats=u.stats
            )
            for i, u in enumerate(team_a)
        ]
        
        team_b_combat = [
            CombatUnit(
                id=f"b_{i}",
                name=u.name,
                hp=u.stats.hp,
                attack=u.stats.attack,
                defense=u.stats.defense,
                attack_speed=u.stats.attack_speed,
                position='front',
                max_mana=u.stats.max_mana,
                skill=u.skill,
                stats=u.stats
            )
            for i, u in enumerate(team_b)
        ]
        
        # Use shared simulator
        self.shared_sim.timeout = timeout
        return self.shared_sim.simulate(team_a_combat, team_b_combat, event_callback, round_number)
