"""
Combat attack processor - handles attack logic and damage calculation
"""
import random
import os
from typing import List, Dict, Any, Callable, Optional
from .event_canonicalizer import emit_mana_change


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

    def _build_unit_attack_payload(
        self,
        attacker: 'CombatUnit',
        target_obj: 'CombatUnit',
        dmg: int,
        side_val: str,
        deliver_ts: float,
        old_hp_val: int,
        new_hp_val: int,
        bonus_attack: bool = False,
        dmg_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build the canonical unit_attack payload for basic attacks."""
        ua = {
            'attacker_id': getattr(attacker, 'id', None),
            'attacker_name': getattr(attacker, 'name', None),
            'attacker_current_mana': getattr(attacker, 'mana', None),
            'attacker_max_mana': getattr(attacker, 'max_mana', None),
            'target_id': getattr(target_obj, 'id', None),
            'target_name': getattr(target_obj, 'name', None),
            'damage': int(dmg) if dmg is not None else 0,
            'damage_type': getattr(attacker, 'damage_type', 'physical'),
            'pre_hp': old_hp_val,
            'post_hp': new_hp_val,
            'applied_damage': int(dmg) if dmg is not None else 0,
            'is_skill': False,
            'bonus_attack': bonus_attack,
            'side': side_val,
            'timestamp': deliver_ts,
        }
        if isinstance(dmg_payload, dict):
            ua['pre_hp'] = dmg_payload.get('pre_hp', ua['pre_hp'])
            ua['post_hp'] = dmg_payload.get('post_hp', ua['post_hp'])
            ua['applied_damage'] = dmg_payload.get('applied_damage', ua['applied_damage'])
            ua['target_hp'] = dmg_payload.get('target_hp', ua.get('post_hp'))
            ua['target_max_hp'] = dmg_payload.get('target_max_hp', getattr(target_obj, 'max_hp', None))
        else:
            ua['target_hp'] = ua['post_hp']
            ua['target_max_hp'] = getattr(target_obj, 'max_hp', None)
        return ua

    def _emit_bonus_basic_attack(
        self,
        unit: 'CombatUnit',
        defending_team: List['CombatUnit'],
        defending_hp: List[int],
        target_idx: int,
        side: str,
        bonus_attack_ts: float,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        compute_ts: float,
        log: List[str],
        attacking_team: List['CombatUnit'],
        attacking_hp: List[int],
    ) -> None:
        """Emit the bonus basic attack that replaces skills at full mana."""
        bonus_target = defending_team[target_idx]
        bonus_damage = self._calculate_damage(unit, bonus_target)
        bonus_old_hp = int(defending_hp[target_idx])
        bonus_new_hp = max(0, bonus_old_hp - int(bonus_damage))
        defending_hp[target_idx] = bonus_new_hp
        emit_mana_change(event_callback, unit, -int(getattr(unit, 'mana', 0) or 0), side=side, timestamp=bonus_attack_ts)
        if event_callback:
            event_callback('unit_attack', self._build_unit_attack_payload(
                unit,
                bonus_target,
                bonus_damage,
                side,
                bonus_attack_ts,
                bonus_old_hp,
                bonus_new_hp,
                bonus_attack=True,
            ))
        if defending_hp[target_idx] <= 0:
            self._process_unit_death(
                unit, defending_team, defending_hp, attacking_team, attacking_hp, target_idx, compute_ts, log, event_callback, side
            )

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
                # Determine mana gain from this attack.
                mana_gain = int(getattr(unit.stats, 'mana_on_attack', 0))
                effective_mana = int(getattr(unit, 'mana', 0)) + int(mana_gain)
                bonus_attack_ready = effective_mana >= getattr(unit, 'max_mana', float('inf'))

                target_idx = self._select_target(attacking_team, defending_team, attacking_hp, defending_hp, i)
                if target_idx is None:
                    # Attacking team wins
                    return "team_a" if side == "team_a" else "team_b"

                # Calculate damage
                damage = self._calculate_damage(unit, defending_team[target_idx])
                old_hp = int(defending_hp[target_idx])
                # Compute new_hp but DO NOT mutate defending_hp here when running under
                # the simulator scheduler. Mutations must happen atomically inside
                # the scheduled action via the canonical emitter (`emit_damage`).
                new_hp = max(0, old_hp - int(damage))
                # print(f"[HP DEBUG] ts={time:.9f} side={side} target={defending_team[target_idx].id}:{defending_team[target_idx].name} old_hp={old_hp} -> new_hp={new_hp} cause=attack damage={damage}")

                # Log and callback
                msg = f"[{time:.2f}s] {side.upper()[0]}:{unit.name} hits {'A' if side == 'team_b' else 'B'}:{defending_team[target_idx].name} for {damage}, hp={defending_hp[target_idx]}"
                log.append(msg)

                # Emit animation_start immediately so UI can play animation
                if event_callback:
                    event_callback('animation_start', {
                        'type': 'animation_start',
                        'animation_id': 'basic_attack',
                        'attacker_id': unit.id,
                        'attacker_name': unit.name,
                        'target_id': defending_team[target_idx].id,
                        'target_name': defending_team[target_idx].name,
                        'duration': 0.2,
                        'timestamp': time
                    })

                # Schedule unit_attack and mana_update with a UI delay (0.2s)
                attack_ts = round(time + 0.2, 10)
                def make_action(attacker, target_obj, dmg, side_val, deliver_ts, old_hp_val, new_hp_val, compute_ts=None, grant_mana=True, reset_mana=False, bonus_attack=False):
                    def action():
                        from .event_canonicalizer import emit_damage, emit_unit_died
                        results = []
                        dmg_payload = None
                        # Prepare hp_arrays and resolve target index at delivery time.
                        # Do not trust scheduled-time index because team composition can change.
                        hp_arrays = None
                        unit_index = None
                        unit_side = None
                        if hasattr(self, 'a_hp') and hasattr(self, 'b_hp'):
                            hp_arrays = {'team_a': self.a_hp, 'team_b': self.b_hp}
                            unit_side = 'team_b' if side_val == 'team_a' else 'team_a'
                            target_team = self.team_b if unit_side == 'team_b' else self.team_a
                            target_id = getattr(target_obj, 'id', None)
                            unit_index = next((idx for idx, u in enumerate(target_team) if getattr(u, 'id', None) == target_id), None)
                            if unit_index is None:
                                raise RuntimeError(f"Target unit {target_id} not found in {unit_side} at delivery_ts={deliver_ts}")

                        # Apply canonical damage mutation without emitting the builtin 'attack' event
                        dmg_payload = emit_damage(None, attacker, target_obj, raw_damage=dmg, shield_absorbed=0, damage_type=getattr(attacker, 'damage_type', 'physical'), side=side_val, timestamp=deliver_ts, cause='attack', emit_event=False, hp_arrays=hp_arrays, unit_index=unit_index, unit_side=unit_side)

                        # Apply mana gain at delivery time before building unit_attack payload.
                        # This keeps server snapshot state and unit_attack payload coherent.
                        mana_payload = None
                        if grant_mana or reset_mana:
                            from .event_canonicalizer import emit_mana_change
                            mana_arrays = None
                            atk_index = None
                            atk_side = None
                            if hasattr(self, 'a_hp') and hasattr(self, 'b_hp'):
                                combat_state = getattr(self, '_combat_state', None)
                                if combat_state is None:
                                    raise RuntimeError("Missing _combat_state during scheduled attack mana emit")
                                mana_arrays = combat_state.mana_arrays
                                atk_side = side_val
                                attacker_team = self.team_a if atk_side == 'team_a' else self.team_b
                                attacker_id = getattr(attacker, 'id', None)
                                atk_index = next((idx for idx, u in enumerate(attacker_team) if getattr(u, 'id', None) == attacker_id), None)
                                if atk_index is None:
                                    raise RuntimeError(f"Attacker unit {attacker_id} not found in {atk_side} at delivery_ts={deliver_ts}")

                            mana_amount = int(getattr(attacker.stats, 'mana_on_attack', 0)) if grant_mana else -int(getattr(attacker, 'mana', 0) or 0)
                            if reset_mana and not grant_mana:
                                mana_amount = -int(getattr(attacker, 'mana', 0) or 0)

                            mana_payload = emit_mana_change(
                                None,
                                attacker,
                                mana_amount,
                                side=side_val,
                                timestamp=deliver_ts,
                                mana_arrays=mana_arrays,
                                unit_index=atk_index,
                                unit_side=atk_side,
                            )

                        ua = self._build_unit_attack_payload(
                            attacker,
                            target_obj,
                            dmg,
                            side_val,
                            deliver_ts,
                            old_hp_val,
                            new_hp_val,
                            bonus_attack=bonus_attack,
                            dmg_payload=dmg_payload,
                        )
                        results.append(('unit_attack', ua))

                        if mana_payload:
                            results.append(('mana_update', mana_payload))

                        # If the canonical damage resulted in death, prepare unit_died
                        # payload and process on-death effects via the modular effect
                        # processor into the local results list so they are emitted
                        # in-order by the simulator sink.
                        if isinstance(dmg_payload, dict) and dmg_payload.get('post_hp') == 0:
                            try:
                                # Mark unit as dead and get canonical died payload
                                died = emit_unit_died(None, target_obj, side=side_val, timestamp=deliver_ts, unit_hp=dmg_payload.get('pre_hp'), hp_arrays=hp_arrays, unit_index=unit_index, unit_side=unit_side)
                                if died:
                                    results.append(('unit_died', died))

                                # If we have a modular_effect_processor available on self,
                                # execute ON_ENEMY_DEATH and ON_ALLY_DEATH triggers using
                                # a local collector that appends events to results so that
                                # they are emitted in-order by the sink.
                                try:
                                    from .modular_effect_processor import TriggerType
                                    if hasattr(self, 'modular_effect_processor') and self.modular_effect_processor:
                                        def _local_collector(ev_type, ev_payload):
                                            results.append((ev_type, ev_payload))

                                        # Build context similar to CombatEffectProcessor
                                        context = {
                                            'current_unit': attacker,
                                            'all_units': attacking_team + defending_team,
                                            'enemy_units': defending_team,
                                            'ally_units': attacking_team,
                                            'collected_stats': getattr(attacker, 'collected_stats', {}),
                                            # Use the original compute timestamp so modular triggers
                                            # see the time the attack was computed (animation_start),
                                            # matching legacy behavior and test expectations.
                                            'current_time': compute_ts if compute_ts is not None else deliver_ts,
                                            'side': side_val,
                                            'player': attacker,
                                            'target_unit': target_obj,
                                            'killer_unit': attacker,
                                            'triggered_rewards': set(),
                                        }

                                        # Process ON_ENEMY_DEATH
                                        try:
                                            self.modular_effect_processor.process_trigger(TriggerType.ON_ENEMY_DEATH, context, _local_collector)
                                        except Exception:
                                            pass

                                        # Process ON_ALLY_DEATH
                                        try:
                                            ally_ctx = {
                                                    'all_units': attacking_team + defending_team,
                                                    'enemy_units': attacking_team,
                                                    'ally_units': defending_team,
                                                    'current_time': compute_ts if compute_ts is not None else deliver_ts,
                                                    'side': 'team_b' if side_val == 'team_a' else 'team_a',
                                                    'dead_ally': target_obj,
                                                    'triggered_rewards': set(),
                                                }
                                            self.modular_effect_processor.process_trigger(TriggerType.ON_ALLY_DEATH, ally_ctx, _local_collector)
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                            except Exception as e:
                                pass

                        return results
                    return action

                # If running under CombatSimulator, use scheduler; otherwise emit immediately
                if hasattr(self, 'schedule_event') and event_callback:
                    action_callable = make_action(unit, defending_team[target_idx], damage, side, attack_ts, old_hp, new_hp, compute_ts=time)
                    # Schedule for delivery at attack_ts
                    # note: CombatSimulator.schedule_event will handle the heap
                    self.schedule_event(attack_ts, action_callable)
                else:
                    # No scheduler available - emit immediate unit_attack
                    if event_callback:
                        # For the non-scheduled path we must apply the HP delta
                        # immediately so downstream logic observing defending_hp
                        # sees the authoritative change.
                        defending_hp[target_idx] = new_hp
                        event_callback('unit_attack', {
                            'attacker_id': unit.id,
                            'attacker_name': unit.name,
                            'target_id': defending_team[target_idx].id,
                            'target_name': defending_team[target_idx].name,
                            'damage': damage,
                            'damage_type': getattr(unit, 'damage_type', 'physical'),
                            'old_hp': old_hp,
                            'new_hp': new_hp,
                            'is_skill': False,
                            'bonus_attack': False,
                            'side': side,
                            'timestamp': attack_ts
                        })

                # Check if target died (only meaningful for non-scheduled path
                # because scheduled deliveries will run death-processing later).
                if not (hasattr(self, 'schedule_event') and event_callback):
                    if defending_hp[target_idx] <= 0:
                        self._process_unit_death(
                            unit, defending_team, defending_hp, attacking_team, attacking_hp, target_idx, time, log, event_callback, side
                        )

                # Post-attack effect processing (lifesteal, mana on attack)
                # Lifesteal: heal attacker by damage * lifesteal%
                ls = getattr(unit, '_computed_stats', None)
                if ls:
                    ls = getattr(ls, 'lifesteal', 0.0)
                else:
                    ls = 0.0
                if ls and damage > 0:
                    heal = int(damage * (ls / 100.0))
                    if heal > 0:
                        # Use canonical emitter for lifesteal healing
                        from .event_canonicalizer import emit_unit_heal
                        emit_unit_heal(
                            event_callback,
                            target=unit,
                            healer=unit,
                            amount=heal,
                            side=side,
                            timestamp=time,
                            current_hp=attacking_hp[i]  # Use authoritative HP from list
                        )
                        log.append(f"{unit.name} lifesteals {heal}")

                # Mana gain: per attack — apply via canonical emitter only for non-scheduled path
                if not (hasattr(self, 'schedule_event') and event_callback):
                    amount = int(getattr(unit.stats, 'mana_on_attack', 0))
                    combat_state = getattr(self, '_combat_state', None)
                    if combat_state is not None:
                        emit_mana_change(event_callback, unit, amount, side=side, timestamp=attack_ts, mana_arrays=combat_state.mana_arrays, unit_index=i, unit_side=side)
                    else:
                        emit_mana_change(event_callback, unit, amount, side=side, timestamp=attack_ts)

                # If mana filled from this attack, queue one extra basic hit.
                if bonus_attack_ready:
                    bonus_attack_ts = round(attack_ts + 0.05, 10)
                    if hasattr(self, 'schedule_event') and event_callback:
                        bonus_action_callable = make_action(
                            unit,
                            defending_team[target_idx],
                            damage,
                            side,
                            bonus_attack_ts,
                            old_hp,
                            new_hp,
                            compute_ts=time,
                            grant_mana=False,
                            reset_mana=True,
                            bonus_attack=True,
                        )
                        self.schedule_event(bonus_attack_ts, bonus_action_callable)
                    elif event_callback:
                        self._emit_bonus_basic_attack(
                            unit,
                            defending_team,
                            defending_hp,
                            target_idx,
                            side,
                            bonus_attack_ts,
                            event_callback,
                            time,
                            log,
                            attacking_team,
                            attacking_hp,
                        )

                if defending_hp[target_idx] > 0:
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

        # Focus logic: if attacker already has a living focused target,
        # keep attacking it until it dies or disappears.
        focused_id = getattr(unit, 'focus_target_id', None)
        if focused_id:
            focused_idx = next((j for j, d in enumerate(defending_team) if getattr(d, 'id', None) == focused_id), None)
            if focused_idx is not None and focused_idx < len(defending_hp) and defending_hp[focused_idx] > 0:
                return focused_idx
            # Focus target unavailable -> clear and select a new one.
            try:
                unit.clear_focus_target()
            except Exception:
                setattr(unit, 'focus_target_id', None)
        
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
            try:
                unit.clear_focus_target()
            except Exception:
                setattr(unit, 'focus_target_id', None)
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

        # Persist focus so subsequent attacks are not random until target changes.
        try:
            unit.focus_target_id = getattr(defending_team[target_idx], 'id', None)
        except Exception:
            setattr(unit, 'focus_target_id', getattr(defending_team[target_idx], 'id', None))

        return target_idx

    def _process_skill_cast(
        self,
        caster: 'CombatUnit',
        target: 'CombatUnit',
        target_hp_list: Optional[List[int]] = None,
        target_idx: Optional[int] = None,
        time: float = 0.0,
        log: Optional[List[str]] = None,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        side: str = 'team_a'
    ):
        """Legacy skill hook kept for compatibility.

        Skills are disabled in the current ruleset, so this method is now a
        no-op and only exists so older call sites do not explode if they still
        reference it.
        """
        return None
