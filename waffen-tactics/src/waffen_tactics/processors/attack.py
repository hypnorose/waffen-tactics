"""
Combat attack processor - separated compute vs apply phases
"""
import random
import os
from typing import List, Dict, Any, Callable, Optional, Tuple
from ..engine.event_dispatcher import EventDispatcher
from ..animation.system import get_animation_system


class CombatAttackProcessor:
    """Handles attack processing with separated compute/apply phases"""

    def __init__(self, event_dispatcher: Optional[EventDispatcher] = None):
        self.event_dispatcher = event_dispatcher

    def _calculate_damage(self, attacker: 'CombatUnit', defender: 'CombatUnit') -> int:
        """Use `compute_damage` from `core.combat_core` as the canonical formula."""
        from waffen_tactics.core.combat_core import compute_damage
        import random
        rng = random.Random()
        return compute_damage(attacker, defender, rng)

    def compute_team_attacks(
        self,
        attacking_team: List['CombatUnit'],
        defending_team: List['CombatUnit'],
        attacking_hp: List[int],
        defending_hp: List[int],
        time: float,
        side: str
    ) -> List[Dict[str, Any]]:
        """Compute all attack events for one team. Returns list of event payloads."""
        events = []
        print(f"[ATTACK_PROC] compute_team_attacks side={side} time={time} attackers={[u.id for u in attacking_team]}")

        # Track mana accumulation for skill casting checks
        mana_accumulation = {}  # unit_id -> total mana gain this tick

        for i, unit in enumerate(attacking_team):
            if attacking_hp[i] <= 0:
                continue

            # Attack if enough time has passed since last attack
            attack_interval = 1.0 / unit.attack_speed if getattr(unit, 'attack_speed', 0) > 0 else float('inf')

            if (time - getattr(unit, 'last_attack_time', 0)) >= attack_interval:
                target_idx = self._select_target(attacking_team, defending_team, attacking_hp, defending_hp, i)
                if target_idx is None:
                    # Attacking team wins - this would be handled by caller
                    continue

                # Calculate damage
                damage = self._calculate_damage(unit, defending_team[target_idx])
                # Determine if this attack should instead trigger a skill cast.
                mana_gain = unit.stats.mana_on_attack
                effective_mana = unit.get_mana() + mana_gain

                skill_casted = False
                if hasattr(unit, 'skill') and unit.skill and effective_mana >= unit.max_mana:
                    # Unit will cast a skill instead of performing this normal attack.
                    # Use the same new-skill execution path as elsewhere to convert
                    # skill executor output into event payloads.
                    skill_data = unit.skill
                    new_skill = None
                    if hasattr(skill_data, 'effects'):
                        new_skill = skill_data
                    elif isinstance(skill_data, dict):
                        new_skill = skill_data.get('effect', {}).get('skill')

                    if new_skill:
                        from waffen_tactics.services.skill_executor import skill_executor
                        from waffen_tactics.models.skill import SkillExecutionContext

                        context = SkillExecutionContext(
                            caster=unit,
                            team_a=attacking_team if side == 'team_a' else defending_team,
                            team_b=defending_team if side == 'team_a' else attacking_team,
                            combat_time=time,
                            event_callback=self.event_dispatcher.emit if getattr(self, 'event_dispatcher', None) is not None else None
                        )

                        skill_events = skill_executor.execute_skill(new_skill, context)
                        for event_type, event_data in skill_events:
                            # Preserve any timestamp emitted by the skill executor; fall back to current compute time
                            ts = event_data.get('timestamp', time) if isinstance(event_data, dict) else time
                            if event_type == 'mana_update':
                                events.append({
                                    'type': 'mana_update',
                                    'unit_id': event_data.get('unit_id'),
                                    'unit_name': event_data.get('unit_name'),
                                    'amount': event_data.get('amount'),
                                    'current_mana': event_data.get('current_mana'),
                                    'side': side,
                                    'timestamp': ts,
                                    'cause': 'skill_cast'
                                })
                            elif event_type == 'unit_attack':
                                events.append({
                                    'type': 'skill_attack',
                                    'attacker_id': event_data.get('attacker_id'),
                                    'target_id': event_data.get('target_id'),
                                    'damage': event_data.get('damage'),
                                    'side': side,
                                    'timestamp': ts,
                                    'is_skill': True
                                })
                            else:
                                # Generic pass-through for other event types: ensure a `type` field
                                if isinstance(event_data, dict):
                                    merged = {'type': event_type}
                                    merged.update(event_data)
                                    if 'timestamp' not in merged:
                                        merged['timestamp'] = ts
                                    events.append(merged)
                                    print(f"[SKILL_EVT] type={event_type} ts={merged.get('timestamp')} caster={getattr(unit,'name',None)} target={defending_team[target_idx].name}")
                                else:
                                    events.append({'type': event_type, 'data': event_data, 'timestamp': ts})
                        # Add a skill_cast marker event
                        events.append({
                            'type': 'skill_cast',
                            'caster_id': unit.id,
                            'caster_name': unit.name,
                            'skill_name': new_skill.name,
                            'target_id': defending_team[target_idx].id,
                            'target_name': defending_team[target_idx].name,
                            'side': side,
                            'timestamp': time,
                            'message': f"{unit.name} casts {new_skill.name}!"
                        })
                        skill_casted = True

                if skill_casted:
                    # Skip creating a normal attack event this tick
                    continue

                # Create attack event payload
                attack_event = {
                    'type': 'unit_attack',
                    'attacker_id': unit.id,
                    'attacker_name': unit.name,
                    'target_id': defending_team[target_idx].id,
                    'target_name': defending_team[target_idx].name,
                    'damage': damage,
                    'pre_hp': defending_hp[target_idx],
                    'side': side,
                    'timestamp': time,
                    'cause': 'attack',
                    'is_skill': False
                }
                events.append(attack_event)

                # Post-attack effects
                # Lifesteal
                ls = getattr(unit, 'lifesteal', 0.0)
                if ls and damage > 0:
                    heal = int(damage * (ls / 100.0))
                    if heal > 0:
                        heal_event = {
                            'type': 'unit_heal',
                            'target_id': unit.id,
                            'target_name': unit.name,
                            'healer_id': unit.id,
                            'healer_name': unit.name,
                            'amount': heal,
                            'side': side,
                            'timestamp': time,
                            'cause': 'lifesteal'
                        }
                        events.append(heal_event)

                # Mana gain
                mana_gain = unit.stats.mana_on_attack
                if mana_gain > 0:
                    mana_event = {
                        'type': 'mana_update',
                        'unit_id': unit.id,
                        'unit_name': unit.name,
                        'amount': mana_gain,
                        'side': side,
                        'timestamp': time,
                        'cause': 'attack'
                    }
                    events.append(mana_event)

                    # Track mana accumulation for skill casting
                    mana_accumulation[unit.id] = mana_accumulation.get(unit.id, 0) + mana_gain


        # Attach UI timing for all emitted events so the frontend can start
        # animations immediately and apply effects after the animation duration.
        return self._attach_ui_timing(events, base_time=time)

    def _attach_ui_timing(self, events: List[Dict[str, Any]], base_time: float) -> List[Dict[str, Any]]:
        """Wrap each event with an immediate `animation_start` event and
        return the original event delayed by the animation duration (annotated
        with `ui_delay`). Operates on dict-shaped events that include a
        `'type'` key. Non-dict or unexpected shapes are passed through.

        This keeps the attack processor deterministic and lets the UI
        control animations separately from authoritative game state.
        """
        timed: List[Dict[str, Any]] = []
        animation_system = get_animation_system()

        for ev in events:
            if not isinstance(ev, dict) or 'type' not in ev:
                timed.append(ev)
                continue

            ev_type = ev.get('type')

            # Map event types to animation IDs (backward compatibility)
            animation_id = self._get_animation_id_for_event(ev_type, ev)

            if animation_id:
                # Use new animation system
                anim_event = animation_system.create_animation_event(
                    animation_id=animation_id,
                    attacker_id=ev.get('attacker_id') or ev.get('unit_id') or ev.get('caster_id'),
                    target_id=ev.get('target_id'),
                    skill_name=ev.get('skill_name') or ev.get('ability'),
                    timestamp=ev.get('timestamp', base_time)
                )
                # Use animation duration as the delay
                delay = anim_event.duration
                anim_payload = {
                    'type': 'animation_start',
                    'animation_id': anim_event.animation_id,
                    'attacker_id': anim_event.attacker_id,
                    'target_id': anim_event.target_id,
                    'skill_name': anim_event.skill_name,
                    'duration': delay,
                    'timestamp': anim_event.timestamp
                }
            else:
                # Fallback to old system for unsupported event types
                delay = 0.2  # Default fallback delay
                anim_payload = {
                    'type': 'animation_start',
                    'animation_type': ev_type,
                    'attacker_id': ev.get('attacker_id') or ev.get('unit_id') or ev.get('caster_id'),
                    'target_id': ev.get('target_id'),
                    'skill_name': ev.get('skill_name') or ev.get('ability'),
                    'duration': delay,
                    'timestamp': ev.get('timestamp', base_time)
                }

            timed.append(anim_payload)

            delayed = dict(ev)
            base_ts = ev.get('timestamp', base_time)
            if base_ts is None:
                base_ts = base_time
            delayed['timestamp'] = base_ts + delay
            delayed['ui_delay'] = delay

            timed.append(delayed)

        return timed

    def _get_animation_id_for_event(self, event_type: str, event: Dict[str, Any]) -> Optional[str]:
        """Map event types to animation IDs for the new system"""
        animation_system = get_animation_system()

        if event_type == 'unit_attack':
            # Check if it's a skill attack
            if event.get('is_skill', False):
                return 'skill_attack'
            else:
                return 'basic_attack'
        elif event_type == 'heal':
            return 'heal'
        elif event_type == 'stat_buff':
            return 'buff'
        elif event_type == 'skill_cast':
            # Could have different animations for different skills
            return 'skill_attack'

        # For other event types, check if there's a registered animation
        # This allows new animations to be added without modifying this code
        registered_ids = animation_system.get_animation_ids()
        if event_type in registered_ids:
            return event_type

        return None

    def apply_attack_events(
        self,
        events: List[Dict[str, Any]],
        combat_state: 'CombatState',
        log: List[str]
    ) -> Optional[str]:
        """Apply computed attack events to combat state. Returns winner if team defeated."""
        winner = None

        for event in events:
            event_type = event['type']

            if event_type == 'unit_attack':
                winner = self._apply_unit_attack(event, combat_state, log)
                if winner:
                    return winner

            elif event_type == 'unit_heal':
                self._apply_unit_heal(event, combat_state, log)

            elif event_type == 'mana_update':
                self._apply_mana_update(event, combat_state)

            elif event_type == 'skill_cast':
                winner = self._apply_skill_cast(event, combat_state, log)
                if winner:
                    return winner

            elif event_type == 'skill_attack':
                winner = self._apply_skill_attack(event, combat_state, log)
                if winner:
                    return winner

        return winner

    def _apply_unit_attack(
        self,
        event: Dict[str, Any],
        combat_state: 'CombatState',
        log: List[str]
    ) -> Optional[str]:
        """Apply a unit attack event."""
        attacker_id = event['attacker_id']
        target_id = event['target_id']
        damage = event['damage']
        side = event['side']
        time = event['timestamp']

        # Find units
        attacker = None
        target = None
        target_idx = None

        if side == 'team_a':
            attacking_team = combat_state.team_a
            defending_team = combat_state.team_b
            defending_hp = combat_state.b_hp
        else:
            attacking_team = combat_state.team_b
            defending_team = combat_state.team_a
            defending_hp = combat_state.a_hp

        for i, unit in enumerate(attacking_team):
            if unit.id == attacker_id:
                attacker = unit
                break

        for i, unit in enumerate(defending_team):
            if unit.id == target_id:
                target = unit
                target_idx = i
                break

        if not attacker or not target or target_idx is None:
            return None

        # Apply damage using canonical emitter — canonical emitter is the
        # single place responsible for mutating `target.hp` and emitting
        # authoritative `unit_attack` payloads. Always allow the canonical
        # emitter to emit so we avoid legacy/duplicate event types.
        from ..services.event_canonicalizer import emit_damage
        emit_damage(
            self.event_dispatcher.emit,
            attacker=attacker,
            target=target,
            raw_damage=damage,
            side=side,
            timestamp=time,
            cause='attack',
            emit_event=True,
        )

        # Update HP list to match unit's new HP
        defending_hp[target_idx] = target.hp

        # Log
        msg = f"[{time:.2f}s] {side.upper()[0]}:{attacker.name} hits {'A' if side == 'team_b' else 'B'}:{target.name} for {damage}, hp={defending_hp[target_idx]}"
        log.append(msg)

        # MARKER: CANONICAL_ONLY — legacy 'attack' event shape removed.
        # Emitters must produce canonical `unit_attack` payloads only.
        # Do not reintroduce legacy shapes; fix producers instead of adding fallbacks.

        # Check if target died
        if defending_hp[target_idx] <= 0:
            winner = self._process_unit_death(
                attacker, defending_team, defending_hp, attacking_team, combat_state.a_hp if side == 'team_a' else combat_state.b_hp, target_idx, time, log, side
            )
            return winner

        return None

    def _apply_unit_heal(
        self,
        event: Dict[str, Any],
        combat_state: 'CombatState',
        log: List[str]
    ):
        """Apply a unit heal event."""
        target_id = event['target_id']
        amount = event['amount']
        side = event['side']
        time = event['timestamp']

        # Find target unit
        target_team = combat_state.team_a if side == 'team_a' else combat_state.team_b
        target = next((u for u in target_team if u.id == target_id), None)
        if not target:
            return

        # Apply heal using canonical emitter
        from ..services.event_canonicalizer import emit_unit_heal
        emit_unit_heal(
            self.event_dispatcher.emit,
            target=target,
            healer=target,  # Self-heal for lifesteal
            amount=amount,
            side=side,
            timestamp=time,
            current_hp=target.hp
        )

        log.append(f"{target.name} lifesteals {amount}")

    def _apply_mana_update(
        self,
        event: Dict[str, Any],
        combat_state: 'CombatState'
    ):
        """Apply a mana update event."""
        unit_id = event['unit_id']
        amount = event['amount']
        side = event['side']
        time = event['timestamp']

        # Find unit
        unit_team = combat_state.team_a if side == 'team_a' else combat_state.team_b
        unit = next((u for u in unit_team if u.id == unit_id), None)
        if not unit:
            return

        # Apply mana change using canonical emitter
        from ..services.event_canonicalizer import emit_mana_update
        current_mana = unit.get_mana() + amount
        emit_mana_update(
            self.event_dispatcher.emit,
            unit,
            current_mana=current_mana,
            side=side,
            timestamp=time
        )

    def _apply_skill_cast(
        self,
        event: Dict[str, Any],
        combat_state: 'CombatState',
        log: List[str]
    ) -> Optional[str]:
        """Apply a skill cast event."""
        caster_id = event['caster_id']
        target_id = event['target_id']
        skill_damage = event.get('damage', 0)
        side = event['side']
        time = event['timestamp']
        skill_name = event['skill_name']

        # Find units
        if side == 'team_a':
            caster_team = combat_state.team_a
            target_team = combat_state.team_b
            target_hp = combat_state.b_hp
        else:
            caster_team = combat_state.team_b
            target_team = combat_state.team_a
            target_hp = combat_state.a_hp

        caster = next((u for u in caster_team if u.id == caster_id), None)
        target = next((u for u in target_team if u.id == target_id), None)
        target_idx = next((i for i, u in enumerate(target_team) if u.id == target_id), None)

        if not caster or not target or target_idx is None:
            return None

        # Reset mana to 0
        mana_reset_amount = -caster.mana
        from ..services.event_canonicalizer import emit_mana_change
        emit_mana_change(
            self.event_dispatcher.emit,
            caster,
            mana_reset_amount,
            side=side,
            timestamp=time
        )

        log.append(f"[{time:.2f}s] {caster.name} casts {skill_name}!")

        # Apply skill damage
        if skill_damage > 0:
            target_hp[target_idx] -= skill_damage
            target_hp[target_idx] = max(0, int(target_hp[target_idx]))
            log.append(f"[{time:.2f}s] {skill_name} deals {skill_damage} damage to {target.name}")

            # Emit skill cast event
            self.event_dispatcher.emit('skill_cast', {
                'caster_id': caster.id,
                'caster_name': caster.name,
                'skill_name': skill_name,
                'target_id': target.id,
                'target_name': target.name,
                'damage': skill_damage,
                'target_hp': target_hp[target_idx],
                'target_max_hp': target.max_hp,
                'side': side,
                'timestamp': time,
                'message': f"{caster.name} casts {skill_name}!"
            })

        # Check if target died from skill
        if target_hp[target_idx] <= 0:
            winner = self._process_unit_death(
                caster, target_team, target_hp, caster_team, combat_state.a_hp if side == 'team_a' else combat_state.b_hp, target_idx, time, log, side
            )
            return winner

        return None

    def _apply_skill_attack(
        self,
        event: Dict[str, Any],
        combat_state: 'CombatState',
        log: List[str]
    ) -> Optional[str]:
        """Apply a skill attack event."""
        attacker_id = event['attacker_id']
        target_id = event['target_id']
        damage = event['damage']
        side = event['side']
        time = event['timestamp']

        # Find units
        attacker = None
        target = None
        target_idx = None

        if side == 'team_a':
            attacking_team = combat_state.team_a
            defending_team = combat_state.team_b
            defending_hp = combat_state.b_hp
        else:
            attacking_team = combat_state.team_b
            defending_team = combat_state.team_a
            defending_hp = combat_state.a_hp

        for i, unit in enumerate(attacking_team):
            if unit.id == attacker_id:
                attacker = unit
                break

        for i, unit in enumerate(defending_team):
            if unit.id == target_id:
                target = unit
                target_idx = i
                break

        if not attacker or not target or target_idx is None:
            return None

        # Apply damage using canonical emitter
        from ..services.event_canonicalizer import emit_damage
        emit_damage(
            self.event_dispatcher.emit,
            attacker=attacker,
            target=target,
            raw_damage=damage,
            side=side,
            timestamp=time,
            cause='skill'
        )

        # Update HP list to match unit's new HP
        defending_hp[target_idx] = target.hp

        # Log
        msg = f"[{time:.2f}s] {side.upper()[0]}:{attacker.name} skill hits {'A' if side == 'team_b' else 'B'}:{target.name} for {damage}, hp={defending_hp[target_idx]}"
        log.append(msg)

        # Check if target died
        if defending_hp[target_idx] <= 0:
            winner = self._process_unit_death(
                attacker, defending_team, defending_hp, attacking_team, combat_state.a_hp if side == 'team_a' else combat_state.b_hp, target_idx, time, log, side
            )
            return winner

        return None

    def _compute_skill_cast(
        self,
        caster: 'CombatUnit',
        target: 'CombatUnit',
        time: float,
        side: str
    ) -> List[Dict[str, Any]]:
        """Compute skill cast events."""
        events = []
        skill = caster.skill

        # Mana reset event (to 0)
        mana_reset_event = {
            'type': 'mana_update',
            'unit_id': caster.id,
            'unit_name': caster.name,
            'amount': -caster.mana,  # Reset to 0
            'side': side,
            'timestamp': time,
            'cause': 'skill_cast'
        }
        events.append(mana_reset_event)

        # Skill cast event
        effect = skill['effect']
        if effect.get('type') == 'damage':
            skill_damage = effect.get('amount', 0)
            skill_event = {
                'type': 'skill_cast',
                'caster_id': caster.id,
                'caster_name': caster.name,
                'skill_name': skill['name'],
                'target_id': target.id,
                'target_name': target.name,
                'damage': skill_damage,
                'side': side,
                'timestamp': time
            }
            events.append(skill_event)

        return events

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

    def _process_team_attacks(
        self,
        attacking_team: List['CombatUnit'],
        defending_team: List['CombatUnit'],
        attacking_hp: List[int],
        defending_hp: List[int],
        time: float,
        log: List[str],
        side: str,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]]
    ) -> Optional[str]:
        """Process attacks for one team. Returns winner if defending team is defeated, None otherwise."""
        # Compute all attack events for this team
        events = self.compute_team_attacks(attacking_team, defending_team, attacking_hp, defending_hp, time, side)
        
        if not events:
            return None

        # Normalize parameter ordering: some callers pass (proc_cb, 'team_a') while
        # others pass ('team_a', proc_cb). Detect and normalize to `side` and
        # `event_cb` variables.
        event_cb = None
        if callable(event_callback) and isinstance(side, str):
            event_cb = event_callback
        else:
            # Older callers may have swapped the args: side is the callback
            if callable(side) and isinstance(event_callback, str):
                event_cb = side
                side = event_callback
            else:
                event_cb = None

        # Emit animation_start events immediately (before applying damage)
        if event_cb:
            for event in events:
                if event.get('type') == 'animation_start':
                    try:
                        event_cb('animation_start', event)
                    except Exception:
                        pass

        # Emit passthrough/meta events (those not handled by apply_attack_events)
        handled_types = {'animation_start', 'unit_attack', 'unit_heal', 'mana_update', 'skill_cast', 'skill_attack'}
        passthrough = [e for e in events if e.get('type') not in handled_types]
        if event_cb:
            for e in passthrough:
                try:
                    event_cb(e.get('type'), e)
                except Exception:
                    pass

        # Create a combat state object for the apply methods
        from ..engine.combat_state import CombatState
        combat_state = CombatState(attacking_team + defending_team, [])
        combat_state.team_a = attacking_team if side == 'team_a' else defending_team
        combat_state.team_b = defending_team if side == 'team_a' else attacking_team
        combat_state.a_hp = attacking_hp if side == 'team_a' else defending_hp
        combat_state.b_hp = defending_hp if side == 'team_a' else attacking_hp

        # Apply only the attack/mana/heal/skill events; animation_start and passthrough events
        # have already been emitted above.
        damage_events = [e for e in events if e.get('type') in ('unit_attack', 'unit_heal', 'mana_update', 'skill_cast', 'skill_attack')]
        winner = self.apply_attack_events(damage_events, combat_state, log)
        
        # Update last attack times for units that attacked
        for event in events:
            if event['type'] == 'unit_attack':
                attacker_id = event['attacker_id']
                attacker = next((u for u in attacking_team if u.id == attacker_id), None)
                if attacker:
                    attacker.last_attack_time = time

        return winner

    def _process_unit_death(
        self,
        killer: 'CombatUnit',
        defending_team: List['CombatUnit'],
        defending_hp: List[int],
        attacking_team: List['CombatUnit'],
        attacking_hp: List[int],
        target_idx: int,
        time: float,
        log: List[str],
        side: str
    ) -> Optional[str]:
        """Process unit death and return winner if team defeated."""
        target = defending_team[target_idx]

        # Emit unit_died event
        from ..services.event_canonicalizer import emit_unit_died
        emit_unit_died(
            self.event_dispatcher.emit,
            unit=target,
            killer=killer,
            side=side,
            timestamp=time
        )

        # Check if entire defending team is defeated
        if all(hp <= 0 for hp in defending_hp):
            return "team_a" if side == "team_a" else "team_b"

        return None