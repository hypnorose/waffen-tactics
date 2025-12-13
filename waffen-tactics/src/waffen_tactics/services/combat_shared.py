"""
Shared combat logic for both Discord bot and web version
"""
import random
from typing import List, Dict, Any, Callable, Optional


class CombatUnit:
    """Lightweight unit representation for combat"""
    def __init__(self, id: str, name: str, hp: int, attack: int, defense: int, attack_speed: float):
        self.id = id
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.attack = attack
        self.defense = defense
        self.attack_speed = attack_speed


class CombatSimulator:
    """Shared combat simulator using tick-based attack speed system"""
    
    def __init__(self, dt: float = 0.1, timeout: int = 120):
        """
        Args:
            dt: Time step in seconds (0.1 = 100ms ticks)
            timeout: Max combat duration in seconds
        """
        self.dt = dt
        self.timeout = timeout
    
    def simulate(
        self, 
        team_a: List[CombatUnit], 
        team_b: List[CombatUnit],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Simulate combat between two teams
        
        Args:
            team_a: First team units
            team_b: Second team units
            event_callback: Optional callback for combat events (type, data)
        
        Returns:
            Dict with winner, duration, survivors, log
        """
        # Track HP separately to avoid mutating input units
        a_hp = [u.hp for u in team_a]
        b_hp = [u.hp for u in team_b]
        log = []
        
        time = 0.0
        
        while time < self.timeout:
            time += self.dt
            
            # Team A attacks
            for i, unit in enumerate(team_a):
                if a_hp[i] <= 0:
                    continue
                
                # Attack chance per tick based on attack speed
                if random.random() < unit.attack_speed * self.dt:
                    # Find alive targets
                    targets = [(j, team_b[j].defense) for j in range(len(team_b)) if b_hp[j] > 0]
                    if not targets:
                        # Team A wins
                        return self._finish_combat("team_a", time, a_hp, b_hp, log)
                    
                    # Target selection: 60% highest defense, 40% random
                    if random.random() < 0.6:
                        target_idx = max(targets, key=lambda x: x[1])[0]
                    else:
                        target_idx = random.choice([t[0] for t in targets])
                    
                    # Calculate damage: LoL-style armor reduction
                    # To deal X damage, you need to deal X * (100 + armor) / 100
                    # Effective damage = attack * 100 / (100 + defense)
                    target_defense = team_b[target_idx].defense
                    damage = unit.attack * 100.0 / (100.0 + target_defense)
                    damage = max(1, damage)  # Minimum 1 damage
                    b_hp[target_idx] -= damage
                    b_hp[target_idx] = max(0, b_hp[target_idx])
                    
                    # Log and callback
                    msg = f"A:{unit.name} hits B:{team_b[target_idx].name} for {damage}, hp={b_hp[target_idx]}"
                    log.append(msg)
                    
                    if event_callback:
                        event_callback('attack', {
                            'attacker_id': unit.id,
                            'attacker_name': unit.name,
                            'target_id': team_b[target_idx].id,
                            'target_name': team_b[target_idx].name,
                            'damage': damage,
                            'target_hp': b_hp[target_idx],
                            'target_max_hp': team_b[target_idx].max_hp,
                            'side': 'team_a'
                        })
                    
                    if b_hp[target_idx] <= 0 and event_callback:
                        event_callback('unit_died', {
                            'unit_id': team_b[target_idx].id,
                            'unit_name': team_b[target_idx].name,
                            'side': 'team_b'
                        })
            
            # Team B attacks
            for i, unit in enumerate(team_b):
                if b_hp[i] <= 0:
                    continue
                
                if random.random() < unit.attack_speed * self.dt:
                    targets = [(j, team_a[j].defense) for j in range(len(team_a)) if a_hp[j] > 0]
                    if not targets:
                        # Team B wins
                        return self._finish_combat("team_b", time, a_hp, b_hp, log)
                    
                    if random.random() < 0.6:
                        target_idx = max(targets, key=lambda x: x[1])[0]
                    else:
                        target_idx = random.choice([t[0] for t in targets])
                    
                    # Calculate damage: LoL-style armor reduction
                    # Effective damage = attack * 100 / (100 + defense)
                    target_defense = team_a[target_idx].defense
                    damage = unit.attack * 100.0 / (100.0 + target_defense)
                    damage = max(1, damage)  # Minimum 1 damage
                    a_hp[target_idx] -= damage
                    a_hp[target_idx] = max(0, a_hp[target_idx])
                    
                    msg = f"B:{unit.name} hits A:{team_a[target_idx].name} for {damage}, hp={a_hp[target_idx]}"
                    log.append(msg)
                    
                    if event_callback:
                        event_callback('attack', {
                            'attacker_id': unit.id,
                            'attacker_name': unit.name,
                            'target_id': team_a[target_idx].id,
                            'target_name': team_a[target_idx].name,
                            'damage': damage,
                            'target_hp': a_hp[target_idx],
                            'target_max_hp': team_a[target_idx].max_hp,
                            'side': 'team_b'
                        })
                    
                    if a_hp[target_idx] <= 0 and event_callback:
                        event_callback('unit_died', {
                            'unit_id': team_a[target_idx].id,
                            'unit_name': team_a[target_idx].name,
                            'side': 'team_a'
                        })
            
            # Check win conditions
            if all(h <= 0 for h in b_hp):
                return self._finish_combat("team_a", time, a_hp, b_hp, log)
            if all(h <= 0 for h in a_hp):
                return self._finish_combat("team_b", time, a_hp, b_hp, log)
        
        # Timeout - winner by total HP
        sum_a = sum(max(0, h) for h in a_hp)
        sum_b = sum(max(0, h) for h in b_hp)
        winner = "team_a" if sum_a >= sum_b else "team_b"
        
        result = self._finish_combat(winner, time, a_hp, b_hp, log)
        result['timeout'] = True
        return result
    
    def _finish_combat(self, winner: str, time: float, a_hp: List[int], b_hp: List[int], log: List[str]) -> Dict[str, Any]:
        """Helper to create result dict"""
        return {
            'winner': winner,
            'duration': time,
            'team_a_survivors': sum(1 for h in a_hp if h > 0),
            'team_b_survivors': sum(1 for h in b_hp if h > 0),
            'log': log
        }
