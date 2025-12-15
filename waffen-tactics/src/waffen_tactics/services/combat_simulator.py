"""
CombatSimulator class - handles combat simulation logic
"""
import random
from typing import List, Dict, Any, Callable, Optional

from .combat_attack_processor import CombatAttackProcessor
from .combat_effect_processor import CombatEffectProcessor
from .combat_regeneration_processor import CombatRegenerationProcessor
from .combat_win_conditions import CombatWinConditionsProcessor
from .combat_per_second_buff_processor import CombatPerSecondBuffProcessor


class CombatSimulator(
    CombatAttackProcessor,
    CombatEffectProcessor,
    CombatRegenerationProcessor,
    CombatWinConditionsProcessor,
    CombatPerSecondBuffProcessor
):
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
        team_a: List['CombatUnit'],
        team_b: List['CombatUnit'],
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
        # Store teams for use in _finish_combat
        self.team_a = team_a
        self.team_b = team_b
        
        # Track HP separately to avoid mutating input units
        a_hp = [u.hp for u in team_a]
        b_hp = [u.hp for u in team_b]
        log = []

        time = 0.0
        last_full_second = -1

        # Debug log
        import logging
        logger = logging.getLogger('waffen_tactics')
        logger.info(f"[COMBAT] Starting simulation with team_a: {[u.name for u in team_a]}, team_b: {[u.name for u in team_b]}")
        logger.info(f"[COMBAT] Team A effects: {[u.effects for u in team_a]}")
        logger.info(f"[COMBAT] Team B effects: {[u.effects for u in team_b]}")

        while time < self.timeout:
            time += self.dt

            # Process attacks for both teams
            winner = self._process_team_attacks(team_a, team_b, a_hp, b_hp, time, log, event_callback, 'team_a')
            if winner:
                return self._finish_combat(winner, time, a_hp, b_hp, log, team_a)

            winner = self._process_team_attacks(team_b, team_a, b_hp, a_hp, time, log, event_callback, 'team_b')
            if winner:
                return self._finish_combat(winner, time, a_hp, b_hp, log, team_b)

            # Apply HP regeneration
            self._process_regeneration(team_a, team_b, a_hp, b_hp, time, log, self.dt, event_callback)

            # Check win conditions
            winner = self._check_win_conditions(a_hp, b_hp)
            if winner:
                logger.info(f"[COMBAT] Win condition met at {time:.2f}s: {winner}, a_hp={a_hp}, b_hp={b_hp}")
                return self._finish_combat(winner, time, a_hp, b_hp, log, team_a if winner == "team_a" else team_b)

            # Per-second buffs: apply once per full second
            current_second = int(time)
            if current_second != last_full_second:
                last_full_second = current_second
                self._process_per_second_buffs(team_a, team_b, a_hp, b_hp, time, log, event_callback)

        # Timeout - winner by total HP
        sum_a = sum(max(0, h) for h in a_hp)
        sum_b = sum(max(0, h) for h in b_hp)
        winner = "team_a" if sum_a >= sum_b else "team_b"

        logger.info(f"[COMBAT] Timeout at {time:.2f}s, winner by HP: {winner}, sum_a={sum_a}, sum_b={sum_b}")
        result = self._finish_combat(winner, time, a_hp, b_hp, log, team_a if winner == "team_a" else team_b)
        result['timeout'] = True
        return result
        """Calculate damage from attacker to defender."""
        # Calculate damage: LoL-style armor reduction
        damage = attacker.attack * 100.0 / (100.0 + defender.defense)
        # Apply target damage reduction if present
        dr = getattr(defender, 'damage_reduction', 0.0)
        if dr:
            damage = damage * (1.0 - dr / 100.0)
        return max(1, int(damage))

    def _finish_combat(self, winner: str, time: float, a_hp: List[int], b_hp: List[int], log: List[str], winning_team: List['CombatUnit']) -> Dict[str, Any]:
        """Helper to create result dict"""
        # Calculate star sum of surviving units from winning team
        surviving_star_sum = 0
        for i, unit in enumerate(winning_team):
            if (winning_team == self.team_a and a_hp[i] > 0) or (winning_team == self.team_b and b_hp[i] > 0):
                surviving_star_sum += getattr(unit, 'star_level', 1)
        
        return {
            'winner': winner,
            'duration': time,
            'team_a_survivors': sum(1 for h in a_hp if h > 0),
            'team_b_survivors': sum(1 for h in b_hp if h > 0),
            'surviving_star_sum': surviving_star_sum,
            'log': log
        }

    def _process_team_attacks(
        self,
        attacking_team: List['CombatUnit'],
        defending_team: List['CombatUnit'],
        attacking_hp: List[int],
        defending_hp: List[int],
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ) -> Optional[str]:
        """Process attacks for one team. Returns winner if defending team is defeated, None otherwise."""
        for i, unit in enumerate(attacking_team):
            if attacking_hp[i] <= 0:
                continue

            # Attack chance per tick based on attack speed
            if random.random() < unit.attack_speed * self.dt:
                # Find alive targets
                targets = [(j, defending_team[j].defense) for j in range(len(defending_team)) if defending_hp[j] > 0]
                if not targets:
                    # Attacking team wins
                    return "team_a" if side == "team_a" else "team_b"

                # Target selection override: if attacker has 'target_least_hp', pick alive target with least current HP
                if any(e.get('type') == 'target_least_hp' for e in getattr(unit, 'effects', [])):
                    target_idx = min([t[0] for t in targets], key=lambda idx: defending_hp[idx])
                else:
                    # Target selection: 60% highest defense, 40% random
                    if random.random() < 0.6:
                        target_idx = max(targets, key=lambda x: x[1])[0]
                    else:
                        target_idx = random.choice([t[0] for t in targets])

                # Calculate damage
                damage = self._calculate_damage(unit, defending_team[target_idx])
                defending_hp[target_idx] -= damage
                defending_hp[target_idx] = max(0, defending_hp[target_idx])

                # Log and callback
                msg = f"[{time:.2f}s] {side.upper()[0]}:{unit.name} hits {'A' if side == 'team_b' else 'B'}:{defending_team[target_idx].name} for {damage}, hp={defending_hp[target_idx]}"
                log.append(msg)

                # Attack callback
                if event_callback:
                    event_callback('attack', {
                        'attacker_id': unit.id,
                        'attacker_name': unit.name,
                        'target_id': defending_team[target_idx].id,
                        'target_name': defending_team[target_idx].name,
                        'damage': damage,
                        'target_hp': defending_hp[target_idx],
                        'target_max_hp': defending_team[target_idx].max_hp,
                        'side': side,
                        'timestamp': time
                    })

                # Post-attack effect processing (lifesteal, mana on attack)
                # Lifesteal: heal attacker by damage * lifesteal%
                ls = getattr(unit, 'lifesteal', 0.0)
                if ls and damage > 0:
                    heal = int(damage * (ls / 100.0))
                    if heal > 0:
                        attacking_hp[i] = min(unit.max_hp, attacking_hp[i] + heal)
                        log.append(f"{unit.name} lifesteals {heal}")

                # Mana gain: per attack
                unit.mana = min(unit.max_mana, unit.mana + unit.stats.mana_on_attack)

                # Send mana update event
                if event_callback:
                    event_callback('mana_update', {
                        'unit_id': unit.id,
                        'unit_name': unit.name,
                        'current_mana': unit.mana,
                        'max_mana': unit.max_mana,
                        'side': side,
                        'timestamp': time
                    })

                # Check for skill casting if mana is full (reaches max_mana)
                if hasattr(unit, 'skill') and unit.skill and unit.mana >= unit.max_mana:
                    self._process_skill_cast(unit, defending_team[target_idx], defending_hp, target_idx, time, log, event_callback, side)

                # Death callback and on-death effect triggers
                if defending_hp[target_idx] <= 0:
                    self._process_unit_death(unit, defending_team, defending_hp, attacking_team, attacking_hp, target_idx, time, log, event_callback, side)
                else:
                    # Target is still alive -> check for on_ally_hp_below triggers on defending team
                    self._process_ally_hp_below_triggers(defending_team, defending_hp, target_idx, time, log, event_callback, side)

        return None

    def _process_skill_cast(
        self,
        caster: 'CombatUnit',
        target: 'CombatUnit',
        target_hp_list: List[int],
        target_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ):
        """Process skill casting for a unit."""
        skill = caster.skill
        caster.mana = 0  # Reset mana to 0 after casting
        log.append(f"[{time:.2f}s] {caster.name} casts {skill['name']}!")

        # Send mana update event after reset
        if event_callback:
            event_callback('mana_update', {
                'unit_id': caster.id,
                'unit_name': caster.name,
                'current_mana': caster.mana,
                'max_mana': caster.max_mana,
                'side': side,
                'timestamp': time
            })

        # Apply skill effect (basic implementation)
        effect = skill['effect']
        if effect.get('type') == 'damage':
            # Deal damage to target
            skill_damage = effect.get('amount', 0)
            target_hp_list[target_idx] -= skill_damage
            target_hp_list[target_idx] = max(0, target_hp_list[target_idx])
            log.append(f"[{time:.2f}s] {skill['name']} deals {skill_damage} damage to {target.name}")

            if event_callback:
                event_callback('skill_cast', {
                    'caster_id': caster.id,
                    'caster_name': caster.name,
                    'skill_name': skill['name'],
                    'target_id': target.id,
                    'target_name': target.name,
                    'damage': skill_damage,
                    'target_hp': target_hp_list[target_idx],
                    'target_max_hp': target.max_hp,
                    'side': side,
                    'timestamp': time,
                    'message': f"{caster.name} casts {skill['name']}!"
                })

        # Check if target died from skill
        if target_hp_list[target_idx] <= 0:
            if event_callback:
                event_callback('unit_died', {
                    'unit_id': target.id,
                    'unit_name': target.name,
                    'side': 'team_a' if side == 'team_b' else 'team_b',
                    'timestamp': time
                })

    def _process_ally_hp_below_triggers(
        self,
        team: List['CombatUnit'],
        hp_list: List[int],
        target_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ):
        """Process on_ally_hp_below triggers for a team."""
        for unit in team:
            for eff in getattr(unit, 'effects', []):
                if eff.get('type') == 'on_ally_hp_below' and not eff.get('_triggered'):
                    thresh = float(eff.get('threshold_percent', 30))
                    heal_pct = float(eff.get('heal_percent', 50))
                    if hp_list[target_idx] <= team[target_idx].max_hp * (thresh / 100.0):
                        heal_amt = int(team[target_idx].max_hp * (heal_pct / 100.0))
                        hp_list[target_idx] = min(team[target_idx].max_hp, hp_list[target_idx] + heal_amt)
                        log.append(f"{unit.name} heals {team[target_idx].name} for {heal_amt} (ally hp below {thresh}%)")
                        if event_callback:
                            event_callback('heal', {
                                'unit_id': team[target_idx].id,
                                'unit_name': team[target_idx].name,
                                'amount': heal_amt,
                                'side': side,
                                'unit_hp': hp_list[target_idx],
                                'unit_max_hp': team[target_idx].max_hp,
                                'timestamp': time
                            })
                        eff['_triggered'] = True
                        break

