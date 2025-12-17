"""
Combat attack processor - handles attack logic and damage calculation
"""
import random
import os
from typing import List, Dict, Any, Callable, Optional


class CombatAttackProcessor:
    """Handles attack processing and damage calculations"""

    def _calculate_damage(self, attacker: 'CombatUnit', defender: 'CombatUnit') -> int:
        """Calculate damage from attacker to defender."""
        damage = attacker.attack * 100.0 / (100.0 + defender.defense)
        # Apply target damage reduction if present
        dr = getattr(defender, 'damage_reduction', 0.0)
        if dr:
            damage = damage * (1.0 - dr / 100.0)
        return max(1, int(damage))  # Minimum 1 damage

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

            # Attack if enough time has passed since last attack
            attack_interval = 1.0 / unit.attack_speed if unit.attack_speed > 0 else float('inf')
            if time - unit.last_attack_time >= attack_interval:
                target_idx = self._select_target(attacking_team, defending_team, attacking_hp, defending_hp, i)
                if target_idx is None:
                    # Attacking team wins
                    return "team_a" if side == "team_a" else "team_b"

                # Calculate damage
                damage = self._calculate_damage(unit, defending_team[target_idx])
                defending_hp[target_idx] -= damage
                defending_hp[target_idx] = max(0, int(defending_hp[target_idx]))

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

                # Check if target died
                if defending_hp[target_idx] <= 0:
                    self._process_unit_death(
                        unit, defending_team, defending_hp, attacking_team, attacking_hp, target_idx, time, log, event_callback, side
                    )

                # Post-attack effect processing (lifesteal, mana on attack)
                # Lifesteal: heal attacker by damage * lifesteal%
                ls = getattr(unit, 'lifesteal', 0.0)
                if ls and damage > 0:
                    heal = int(damage * (ls / 100.0))
                    if heal > 0:
                        attacking_hp[i] = min(unit.max_hp, int(attacking_hp[i] + heal))
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
                skill_was_cast = False
                target_was_alive_before_skill = defending_hp[target_idx] > 0
                if hasattr(unit, 'skill') and unit.skill and unit.mana >= unit.max_mana:
                    skill_was_cast = True
                    self._process_skill_cast(unit, defending_team[target_idx], defending_hp, target_idx, time, log, event_callback, side)

                # Death callback and on-death effect triggers
                # Only process death if target died from skill (attack death was already processed above)
                if defending_hp[target_idx] <= 0 and skill_was_cast and target_was_alive_before_skill:
                    self._process_unit_death(unit, defending_team, defending_hp, attacking_team, attacking_hp, target_idx, time, log, event_callback, side)
                elif defending_hp[target_idx] > 0:
                    # Target is still alive -> check for on_ally_hp_below triggers on defending team
                    self._process_ally_hp_below_triggers(defending_team, defending_hp, target_idx, time, log, event_callback, side)

                # Update last attack time
                unit.last_attack_time = time

        return None

    def _select_target(
        self,
        attacking_team: List['CombatUnit'],
        defending_team: List['CombatUnit'],
        attacking_hp: List[int],
        defending_hp: List[int],
        attacker_idx: int
    ) -> Optional[int]:
        """Select a target for the attacking unit at index attacker_idx."""
        unit = attacking_team[attacker_idx]
        
        # Find alive targets and split by line
        front_targets = [(j, defending_team[j].defense) for j in range(len(defending_team)) if defending_hp[j] > 0 and defending_team[j].position == 'front']
        back_targets = [(j, defending_team[j].defense) for j in range(len(defending_team)) if defending_hp[j] > 0 and defending_team[j].position == 'back']

        # Default ordering: front line first then back line
        targets = front_targets + back_targets
        # If unit has a 'target_backline' effect, prefer backline targets first
        has_backline = False
        for e in getattr(unit, 'effects', []) or []:
            if isinstance(e, dict) and e.get('type') == 'target_backline':
                has_backline = True
                break
            if isinstance(e, str) and e == 'target_backline':
                has_backline = True
                break
        if has_backline:
            targets = back_targets + front_targets
        if not targets:
            return None

        # Feature flag: when WAFFEN_DETERMINISTIC_TARGETING=1 the selection is deterministic
        # Default behaviour (when the var is not set) is to select randomly within the preferred line.
        DETERMINISTIC_TARGETING = os.getenv('WAFFEN_DETERMINISTIC_TARGETING', '0') in ('1', 'true', 'True')

        # Target selection override: if attacker has 'target_least_hp', pick alive target with least current HP
        if any(e.get('type') == 'target_least_hp' for e in getattr(unit, 'effects', [])):
            target_idx = min([t[0] for t in targets], key=lambda idx: defending_hp[idx])
        else:
            # Deterministic override: when the env var is set we pick the first-in-priority list.
            # Otherwise (default) pick a random target within the preferred line.
            if DETERMINISTIC_TARGETING:
                target_idx = targets[0][0]
            else:
                if has_backline:
                    preferred = back_targets if back_targets else front_targets
                else:
                    preferred = front_targets if front_targets else back_targets

                candidate_list = preferred if preferred else targets
                target_idx = random.choice([t[0] for t in candidate_list])

        return target_idx

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
            target_hp_list[target_idx] = max(0, int(target_hp_list[target_idx]))
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
            # Use _process_unit_death to handle trait effects properly
            self._process_unit_death(caster, [target], target_hp_list, [caster], [caster.max_hp], target_idx, time, log, event_callback, side)