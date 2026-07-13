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

        # Track mana accumulation for the bonus basic attack check.
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

                # Convenience: event callback used by emitters (may be None)
                event_callback = self.event_dispatcher.emit if getattr(self, 'event_dispatcher', None) is not None else None

                # Calculate damage
                damage = self._calculate_damage(unit, defending_team[target_idx])
                # Skills are disabled in the current ruleset.
                # When mana is full, the unit simply gets one extra basic attack.
                mana_gain = unit.stats.mana_on_attack
                effective_mana = unit.get_mana() + mana_gain

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
                    'bonus_attack': False,
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
                    from ..services.event_canonicalizer import emit_mana_change
                    if hasattr(self, 'a_mana') and hasattr(self, 'b_mana'):
                        mana_arrays = {'team_a': self.a_mana, 'team_b': self.b_mana}
                        emit_mana_change(event_callback, unit, mana_gain, side=side, timestamp=time, mana_arrays=mana_arrays, unit_index=i, unit_side=side)
                    else:
                        emit_mana_change(event_callback, unit, mana_gain, side=side, timestamp=time)

                    # Track mana accumulation for skill casting
                    mana_accumulation[unit.id] = mana_accumulation.get(unit.id, 0) + mana_gain

                if effective_mana >= unit.max_mana:
                    bonus_attack = {
                        'type': 'unit_attack',
                        'attacker_id': unit.id,
                        'attacker_name': unit.name,
                        'target_id': defending_team[target_idx].id,
                        'target_name': defending_team[target_idx].name,
                        'damage': damage,
                        'pre_hp': defending_hp[target_idx],
                        'side': side,
                        'timestamp': round(time + 0.05, 10),
                        'cause': 'attack',
                        'bonus_attack': True,
                    }
                    events.append(bonus_attack)
                    if mana_gain > 0:
                        events.append({
                            'type': 'mana_update',
                            'unit_id': unit.id,
                            'unit_name': unit.name,
                            'amount': -unit.max_mana,
                            'current_mana': 0,
                            'side': side,
                            'timestamp': round(time + 0.05, 10),
                            'cause': 'attack',
                        })


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
            return 'basic_attack'
        elif event_type == 'heal':
            return 'heal'
        elif event_type == 'stat_buff':
            return 'buff'

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

        # Prepare HP arrays for canonical emitter to update atomically
        hp_arrays = {'team_a': combat_state.a_hp, 'team_b': combat_state.b_hp}
        defending_side = 'team_b' if side == 'team_a' else 'team_a'

        emit_damage(
            self.event_dispatcher.emit,
            attacker=attacker,
            target=target,
            raw_damage=damage,
            side=side,
            timestamp=time,
            cause='attack',
            emit_event=True,
            hp_arrays=hp_arrays,
            unit_index=target_idx,
            unit_side=defending_side,
        )

        # HP array is now updated atomically by emit_damage - no manual sync needed

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
        """Apply a mana update event.
        
        NOTE: Mana changes are already applied by canonical emitters during compute phase.
        This method exists only for event processing consistency but does not re-apply changes.
        """
        pass

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

        def _normalize_preference(value: Any) -> Optional[str]:
            if not value:
                return None
            mapping = {
                'back': 'backline',
                'backline': 'backline',
                'front': 'frontline',
                'frontline': 'frontline',
                'lowest_hp': 'lowest_hp',
                'weakest': 'lowest_hp',
                'highest_hp': 'highest_hp',
                'tank': 'highest_hp',
            }
            return mapping.get(str(value).lower())

        def _get_target_preference() -> Optional[str]:
            for e in reversed(getattr(unit, 'effects', []) or []):
                if isinstance(e, dict) and e.get('type') == 'targeting_preference':
                    pref = _normalize_preference(e.get('preference'))
                    if pref:
                        return pref
            # legacy support
            for e in getattr(unit, 'effects', []) or []:
                if isinstance(e, dict) and e.get('type') == 'target_backline':
                    return 'backline'
                if isinstance(e, str) and e == 'target_backline':
                    return 'backline'
                if isinstance(e, dict) and e.get('type') == 'target_least_hp':
                    return 'lowest_hp'
            return None

        # Find alive targets and split by line
        front_targets = [(j, defending_team[j].defense) for j in range(len(defending_team)) if defending_hp[j] > 0 and defending_team[j].position == 'front']
        back_targets = [(j, defending_team[j].defense) for j in range(len(defending_team)) if defending_hp[j] > 0 and defending_team[j].position == 'back']

        # Default ordering: front line first then back line
        targets = front_targets + back_targets
        preference = _get_target_preference()
        if preference == 'backline':
            targets = back_targets + front_targets
        if not targets:
            return None

        # Feature flag: when WAFFEN_DETERMINISTIC_TARGETING=1 the selection is deterministic
        # Default behaviour (when the var is not set) is to select randomly within the preferred line.
        DETERMINISTIC_TARGETING = os.getenv('WAFFEN_DETERMINISTIC_TARGETING', '0') in ('1', 'true', 'True')

        # Target selection override: support target preference effects and legacy targeting hooks.
        if preference in ('lowest_hp', 'highest_hp'):
            chooser = min if preference == 'lowest_hp' else max
            target_idx = chooser([t[0] for t in targets], key=lambda idx: defending_hp[idx])
        else:
            candidate_list = targets
            if preference == 'backline':
                candidate_list = back_targets if back_targets else front_targets
            elif preference == 'frontline':
                candidate_list = front_targets if front_targets else back_targets

            if not candidate_list:
                candidate_list = targets

            # Deterministic override: when the env var is set we pick the first-in-priority list.
            # Otherwise (default) pick a random target within the preferred line.
            if DETERMINISTIC_TARGETING:
                target_idx = candidate_list[0][0]
            else:
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
        handled_types = {'animation_start', 'unit_attack', 'unit_heal', 'mana_update'}
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
        damage_events = [e for e in events if e.get('type') in ('unit_attack', 'unit_heal', 'mana_update')]
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
            recipient=target,
            side=side,
            timestamp=time
        )

        # Check if entire defending team is defeated
        if all(hp <= 0 for hp in defending_hp):
            return "team_a" if side == "team_a" else "team_b"

        return None
