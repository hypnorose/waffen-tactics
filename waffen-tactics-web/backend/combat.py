"""
Shared combat logic for both Discord bot and web version
"""
import random
from typing import List, Dict, Any, Callable, Optional


class CombatUnit:
    """Lightweight unit representation for combat"""
    def __init__(self, id: str, name: str, hp: int, attack: int, defense: int, attack_speed: float, star_level: int = 1, position: str = 'front', effects: Optional[List[Dict[str, Any]]] = None, max_mana: int = 100, mana_regen: int = 0, stats: Optional[Dict[str, Any]] = None, skill: Optional[Dict[str, Any]] = None):
        self.id = id
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.attack = attack
        self.defense = defense
        self.attack_speed = attack_speed
        self.star_level = star_level
        self.position = position  # 'front' or 'back'
        self.effects = effects or []
        self.max_mana = max_mana
        self.mana = 0
        self.mana_regen = mana_regen
        self.stats = stats
        self.skill = skill


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
                
                    # Check if unit has target_least_hp effect
                    has_least_hp_targeting = any(effect.get('type') == 'target_least_hp' for effect in unit.effects or [])
                    
                    # Find alive targets - prioritize front line units
                    if has_least_hp_targeting:
                        front_targets = [(j, b_hp[j]) for j in range(len(team_b)) if b_hp[j] > 0 and team_b[j].position == 'front']
                        back_targets = [(j, b_hp[j]) for j in range(len(team_b)) if b_hp[j] > 0 and team_b[j].position == 'back']
                    else:
                        front_targets = [(j, team_b[j].defense) for j in range(len(team_b)) if b_hp[j] > 0 and team_b[j].position == 'front']
                        back_targets = [(j, team_b[j].defense) for j in range(len(team_b)) if b_hp[j] > 0 and team_b[j].position == 'back']
                    
                    # Target front line first, then back line
                    if front_targets:
                        targets = front_targets
                    else:
                        targets = back_targets
                    
                    if not targets:
                        # Team A wins
                        return self._finish_combat("team_a", time, a_hp, b_hp, log, team_a)
                    
                    # Target selection
                    if has_least_hp_targeting:
                        # Always target lowest HP
                        target_idx = min(targets, key=lambda x: x[1])[0]
                    else:
                        # 60% highest defense, 40% random
                        if random.random() < 0.6:
                            target_idx = max(targets, key=lambda x: x[1])[0]
                        else:
                            target_idx = random.choice([t[0] for t in targets])
                    
                    # Calculate damage: attack - defense, min 1
                    damage = max(1, unit.attack - team_b[target_idx].defense)
                    try:
                        old_hp = int(b_hp[target_idx])
                    except Exception:
                        old_hp = b_hp[target_idx]
                    b_hp[target_idx] -= damage
                    b_hp[target_idx] = max(0, b_hp[target_idx])
                    try:
                        new_hp = int(b_hp[target_idx])
                    except Exception:
                        new_hp = b_hp[target_idx]
                    # print(f"[HP DEBUG] ts={time:.9f} side=team_a target={team_b[target_idx].id}:{team_b[target_idx].name} old_hp={old_hp} -> new_hp={new_hp} cause=attack damage={damage}")
                    
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
                            'side': 'team_a',
                            'timestamp': time
                        })
                    
                    if b_hp[target_idx] <= 0 and event_callback:
                        event_callback('unit_died', {
                            'unit_id': team_b[target_idx].id,
                            'unit_name': team_b[target_idx].name,
                            'side': 'team_b',
                            'timestamp': time
                        })
            
            # Team B attacks
            for i, unit in enumerate(team_b):
                if b_hp[i] <= 0:
                    continue
                
                if random.random() < unit.attack_speed * self.dt:
                    # Check if unit has target_least_hp effect
                    has_least_hp_targeting = any(effect.get('type') == 'target_least_hp' for effect in unit.effects or [])
                    
                    # Find alive targets - prioritize front line units
                    if has_least_hp_targeting:
                        front_targets = [(j, a_hp[j]) for j in range(len(team_a)) if a_hp[j] > 0 and team_a[j].position == 'front']
                        back_targets = [(j, a_hp[j]) for j in range(len(team_a)) if a_hp[j] > 0 and team_a[j].position == 'back']
                    else:
                        front_targets = [(j, team_a[j].defense) for j in range(len(team_a)) if a_hp[j] > 0 and team_a[j].position == 'front']
                        back_targets = [(j, team_a[j].defense) for j in range(len(team_a)) if a_hp[j] > 0 and team_a[j].position == 'back']
                    
                    # Target front line first, then back line
                    if front_targets:
                        targets = front_targets
                    else:
                        targets = back_targets
                    
                    if not targets:
                        # Team B wins
                        return self._finish_combat("team_b", time, a_hp, b_hp, log, team_b)
                    
                    # Target selection
                    if has_least_hp_targeting:
                        # Always target lowest HP
                        target_idx = min(targets, key=lambda x: x[1])[0]
                    else:
                        # 60% highest defense, 40% random
                        if random.random() < 0.6:
                            target_idx = max(targets, key=lambda x: x[1])[0]
                        else:
                            target_idx = random.choice([t[0] for t in targets])
                    
                    damage = max(1, unit.attack - team_a[target_idx].defense)
                    try:
                        old_hp = int(a_hp[target_idx])
                    except Exception:
                        old_hp = a_hp[target_idx]
                    a_hp[target_idx] -= damage
                    a_hp[target_idx] = max(0, a_hp[target_idx])
                    try:
                        new_hp = int(a_hp[target_idx])
                    except Exception:
                        new_hp = a_hp[target_idx]
                    # print(f"[HP DEBUG] ts={time:.9f} side=team_b target={team_a[target_idx].id}:{team_a[target_idx].name} old_hp={old_hp} -> new_hp={new_hp} cause=attack damage={damage}")
                    
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
                            'side': 'team_b',
                            'timestamp': time
                        })
                    
                    if a_hp[target_idx] <= 0 and event_callback:
                        event_callback('unit_died', {
                            'unit_id': team_a[target_idx].id,
                            'unit_name': team_a[target_idx].name,
                            'side': 'team_a',
                            'timestamp': time
                        })
            
            # Check win conditions
            if all(h <= 0 for h in b_hp):
                return self._finish_combat("team_a", time, a_hp, b_hp, log, team_a)
            if all(h <= 0 for h in a_hp):
                return self._finish_combat("team_b", time, a_hp, b_hp, log, team_b)
        
        # Timeout - winner by total HP
        sum_a = sum(max(0, h) for h in a_hp)
        sum_b = sum(max(0, h) for h in b_hp)
        winner = "team_a" if sum_a >= sum_b else "team_b"
        
        result = self._finish_combat(winner, time, a_hp, b_hp, log, team_a if winner == "team_a" else team_b)
        result['timeout'] = True
        return result
    
    def _finish_combat(self, winner: str, time: float, a_hp: List[int], b_hp: List[int], log: List[str], winning_team: List[CombatUnit]) -> Dict[str, Any]:
        """Helper to create result dict"""
        # Calculate star sum of surviving units from winning team
        surviving_star_sum = 0
        print(f"DEBUG _finish_combat: winner={winner}, winning_team is team_a: {winning_team == team_a}")
        for i, unit in enumerate(winning_team):
            hp_check = (winning_team == team_a and a_hp[i] > 0) or (winning_team == team_b and b_hp[i] > 0)
            star_level = getattr(unit, 'star_level', 1)
            print(f"DEBUG unit {i}: {unit.name}, star_level={star_level}, hp_check={hp_check}")
            if hp_check:
                surviving_star_sum += star_level
        print(f"DEBUG surviving_star_sum = {surviving_star_sum}")
        
        return {
            'winner': winner,
            'duration': time,
            'team_a_survivors': sum(1 for h in a_hp if h > 0),
            'team_b_survivors': sum(1 for h in b_hp if h > 0),
            'surviving_star_sum': surviving_star_sum,
            'log': log
        }
