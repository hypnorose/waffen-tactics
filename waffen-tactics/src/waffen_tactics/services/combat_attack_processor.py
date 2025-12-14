"""
Combat attack processor - handles attack logic and damage calculation
"""
import random
from typing import List, Dict, Any, Callable, Optional


class CombatAttackProcessor:
    """Handles attack processing and damage calculations"""

    def _calculate_damage(self, attacker: 'CombatUnit', defender: 'CombatUnit') -> int:
        """Calculate damage from attacker to defender."""
        # Calculate damage: LoL-style armor reduction
        damage = attacker.attack * 100.0 / (100.0 + defender.defense)
        # Apply target damage reduction if present
        dr = getattr(defender, 'damage_reduction', 0.0)
        if dr:
            damage = damage * (1.0 - dr / 100.0)
        return max(1, damage)  # Minimum 1 damage

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

                # Mana gain: +10 per attack
                unit.mana = min(unit.max_mana, unit.mana + 10)

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