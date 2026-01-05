"""
Combat attack processor - handles attack logic and damage calculation
"""
import random
import os
from typing import List, Dict, Any, Callable, Optional
from .event_canonicalizer import emit_mana_update
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
                # Determine mana gain from this attack (used to decide casting)
                mana_gain = int(getattr(unit.stats, 'mana_on_attack', 0))

                # If unit can cast a skill right now (including mana that would be gained from this attack), prefer skill over basic attack
                effective_mana = int(getattr(unit, 'mana', 0)) + int(mana_gain)
                if hasattr(unit, 'skill') and unit.skill and effective_mana >= getattr(unit, 'max_mana', float('inf')):
                    # Apply mana gain first so skill casting has the mana available
                    combat_state = getattr(self, '_combat_state', None)
                    if combat_state is not None:
                        emit_mana_change(event_callback, unit, mana_gain, side=side, timestamp=time, mana_arrays=combat_state.mana_arrays, unit_index=i, unit_side=side)
                    else:
                        emit_mana_change(event_callback, unit, mana_gain, side=side, timestamp=time)
                    target_idx = self._select_target(attacking_team, defending_team, attacking_hp, defending_hp, i)
                    if target_idx is None:
                        return "team_a" if side == "team_a" else "team_b"
                    # Invoke skill cast using canonical signature
                    self._process_skill_cast(
                        caster=unit,
                        target=defending_team[target_idx],
                        target_hp_list=defending_hp,
                        target_idx=target_idx,
                        time=time,
                        log=log,
                        event_callback=event_callback,
                        side=side,
                    )
                    # Update HP list from unit.hp (skills mutate unit.hp)
                    defending_hp[target_idx] = defending_team[target_idx].hp
                    # Check if target died from skill
                    if defending_hp[target_idx] <= 0:
                        winner = self._process_unit_death(unit, defending_team, defending_hp, attacking_team, attacking_hp, target_idx, time, log, event_callback, side)
                        if winner:
                            return winner
                    # mark last attack time as this time (skill uses the attack slot)
                    unit.last_attack_time = time
                    # After skill cast, continue to next unit (no basic attack this tick)
                    continue

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
                def make_action(attacker, target_obj, dmg, side_val, deliver_ts, old_hp_val, new_hp_val, target_idx_arg=None, compute_ts=None):
                    def action():
                        from .event_canonicalizer import emit_damage, emit_unit_died
                        results = []
                        dmg_payload = None
                        # Prepare hp_arrays and unit side/index for atomic updates when running under simulator
                        hp_arrays = None
                        unit_index = None
                        unit_side = None
                        try:
                            if hasattr(self, 'a_hp') and hasattr(self, 'b_hp'):
                                hp_arrays = {'team_a': self.a_hp, 'team_b': self.b_hp}
                                # target_idx_arg references index inside defending_team
                                unit_index = int(target_idx_arg) if target_idx_arg is not None else None
                                # target side is opposite of attacker side
                                unit_side = 'team_b' if side_val == 'team_a' else 'team_a'
                        except Exception:
                            hp_arrays = None

                        # Apply canonical damage mutation without emitting the builtin 'attack' event
                        dmg_payload = emit_damage(None, attacker, target_obj, raw_damage=dmg, shield_absorbed=0, damage_type=getattr(attacker, 'damage_type', 'physical'), side=side_val, timestamp=deliver_ts, cause='attack', emit_event=False, hp_arrays=hp_arrays, unit_index=unit_index, unit_side=unit_side)

                        # Build unit_attack payload with authoritative HP fields
                        ua = {
                            'attacker_id': getattr(attacker, 'id', None),
                            'attacker_name': getattr(attacker, 'name', None),
                            'target_id': getattr(target_obj, 'id', None),
                            'target_name': getattr(target_obj, 'name', None),
                            'damage': int(dmg) if dmg is not None else 0,
                            'damage_type': getattr(attacker, 'damage_type', 'physical'),
                            'pre_hp': None,
                            'post_hp': None,
                            'applied_damage': int(dmg) if dmg is not None else 0,
                            'is_skill': False,
                            'side': side_val,
                            'timestamp': deliver_ts,
                        }

                        # Fill HP info preferentially from dmg_payload
                        if isinstance(dmg_payload, dict):
                            ua['pre_hp'] = dmg_payload.get('pre_hp')
                            ua['post_hp'] = dmg_payload.get('post_hp')
                            ua['applied_damage'] = dmg_payload.get('applied_damage', ua['applied_damage'])
                            # Ensure backward-compatible authoritative HP fields
                            ua['target_hp'] = dmg_payload.get('target_hp', ua.get('post_hp'))
                            ua['target_max_hp'] = dmg_payload.get('target_max_hp', getattr(target_obj, 'max_hp', None))
                        else:
                            ua['pre_hp'] = old_hp_val
                            ua['post_hp'] = getattr(target_obj, 'hp', new_hp_val)
                            ua['target_hp'] = ua['post_hp']
                            ua['target_max_hp'] = getattr(target_obj, 'max_hp', None)

                        # Warn if canonical dmg_payload is missing authoritative fields
                        try:
                            missing = []
                            if isinstance(dmg_payload, dict):
                                if 'post_hp' not in dmg_payload:
                                    missing.append('post_hp')
                                # some emitters may use 'unit_id' rather than 'target_id'
                                if dmg_payload.get('unit_id') is None and ua.get('target_id') is None:
                                    missing.append('target_id')
                            else:
                                # dmg_payload not a dict (unexpected) — warn
                                missing.append('dmg_payload_not_dict')
                            if missing:
                                print(f"[MAKE_ACTION WARN] missing_fields={missing} attacker={getattr(attacker,'id',None)} target={getattr(target_obj,'id',None)} deliver_ts={deliver_ts} dmg_payload={dmg_payload}")
                        except Exception:
                            pass

                        results.append(('unit_attack', ua))

                        # DEBUG: log dmg_payload contents to help trace missing unit_died
                        try:
                            print(f"[MAKE_ACTION DEBUG] dmg_payload={dmg_payload}")
                        except Exception:
                            pass

                        # If the canonical damage resulted in death, prepare unit_died
                        # payload and process on-death effects via the modular effect
                        # processor into the local results list so they are emitted
                        # in-order by the simulator sink.
                        if isinstance(dmg_payload, dict) and dmg_payload.get('post_hp') == 0:
                            try:
                                # Mark unit as dead and get canonical died payload
                                died = emit_unit_died(None, target_obj, side=side_val, timestamp=deliver_ts, unit_hp=dmg_payload.get('pre_hp'), hp_arrays=hp_arrays, unit_index=unit_index, unit_side=unit_side)
                                print(f"[MAKE_ACTION DEBUG] emit_unit_died returned: {died}")
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
                                print(f"[MAKE_ACTION ERROR] emit_unit_died raised: {e}")

                        # Emit mana_update snapshot for attacker at deliver_ts
                        mu = {
                            'unit_id': getattr(attacker, 'id', None),
                            'unit_name': getattr(attacker, 'name', None),
                            'current_mana': getattr(attacker, 'mana', None),
                            'max_mana': getattr(attacker, 'max_mana', None),
                            'unit_hp': getattr(attacker, 'hp', None),  # AUTHORITATIVE: current HP
                            'side': side_val,
                            'timestamp': deliver_ts,
                        }
                        results.append(('mana_update', mu))
                        return results
                    return action

                # If running under CombatSimulator, use scheduler; otherwise emit immediately
                if hasattr(self, 'schedule_event') and event_callback:
                    action_callable = make_action(unit, defending_team[target_idx], damage, side, attack_ts, old_hp, new_hp, target_idx_arg=target_idx, compute_ts=time)
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

                # Mana gain: per attack — apply via canonical emitter (mutates state)
                amount = int(getattr(unit.stats, 'mana_on_attack', 0))
                combat_state = getattr(self, '_combat_state', None)
                if combat_state is not None:
                    emit_mana_change(event_callback, unit, amount, side=side, timestamp=attack_ts, mana_arrays=combat_state.mana_arrays, unit_index=i, unit_side=side)
                else:
                    emit_mana_change(event_callback, unit, amount, side=side, timestamp=attack_ts)

                # Check for skill casting if mana is full (reaches max_mana)
                skill_was_cast = False
                target_was_alive_before_skill = defending_hp[target_idx] > 0
                if hasattr(unit, 'skill') and unit.skill and unit.mana >= unit.max_mana:
                    skill_was_cast = True
                    # Call using keyword args so mocks/tests receive named parameters
                    self._process_skill_cast(
                        caster=unit,
                        target=defending_team[target_idx],
                        target_hp_list=defending_hp,
                        target_idx=target_idx,
                        time=time,
                        log=log,
                        event_callback=event_callback,
                        side=side,
                    )

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
        target_hp_list: Optional[List[int]] = None,
        target_idx: Optional[int] = None,
        time: float = 0.0,
        log: Optional[List[str]] = None,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        side: str = 'team_a'
    ):
        """Process skill casting for a unit."""
        # Allow callers to invoke with old signature: (caster, target, time=..., log=..., event_callback=..., side=...)
        # If target_hp_list/target_idx are not provided, build minimal lists so downstream death handling can operate.
        if target_hp_list is None or target_idx is None:
            # find target in simulator teams if available
            if hasattr(self, 'team_a') and hasattr(self, 'team_b'):
                teams = list(getattr(self, 'team_a', [])) + list(getattr(self, 'team_b', []))
                if target in teams:
                    idx = teams.index(target)
                    if idx < len(getattr(self, 'team_a', [])):
                        target_hp_list = getattr(self, 'a_hp', [getattr(target, 'hp', 0)])
                        target_idx = idx
                    else:
                        target_hp_list = getattr(self, 'b_hp', [getattr(target, 'hp', 0)])
                        target_idx = idx - len(getattr(self, 'team_a', []))
                else:
                    target_hp_list = [getattr(target, 'hp', 0)]
                    target_idx = 0
            else:
                target_hp_list = [getattr(target, 'hp', 0)]
                target_idx = 0
        if log is None:
            log = []
        skill = caster.skill
        log.append(f"[{time:.2f}s] {caster.name} casts {skill.get('name', getattr(skill, 'name', '<skill>'))}!")

        # New skill system: if the stored `skill` is a wrapper dict containing
        # a Skill object under ['effect']['skill'], delegate to the SkillExecutor
        # so effects like `delay` and `damage_over_time` are executed correctly.
        new_skill = None
        if isinstance(skill, dict):
            if 'effects' in skill:
                # Convert dict to Skill object
                from ..models.skill import Skill
                new_skill = Skill.from_dict(skill)
            elif 'effect' in skill:
                # Old format: 'effect' contains a single effect dict
                # New format: 'effect' contains {'skill': Skill}
                # Convert to new format
                effect = skill['effect']
                if isinstance(effect, dict):
                    if 'skill' in effect:
                        # New format
                        new_skill = effect['skill']
                    else:
                        # Old format: convert single effect to list
                        skill_dict = skill.copy()
                        skill_dict['effects'] = [effect]
                        skill_dict['mana_cost'] = skill.get('cost', 0)
                        del skill_dict['effect']
                        from ..models.skill import Skill
                        new_skill = Skill.from_dict(skill_dict)
                else:
                    # effect is already a skill object or something else
                    new_skill = effect
            else:
                new_skill = skill.get('effect', {}).get('skill')
        elif hasattr(skill, 'effects'):
            new_skill = skill

        if new_skill is not None:
            from .skill_executor import skill_executor
            from ..models.skill import SkillExecutionContext
            ctx = SkillExecutionContext(
                caster=caster,
                team_a=getattr(self, 'team_a', []) if side == 'team_a' else getattr(self, 'team_b', []),
                team_b=getattr(self, 'team_b', []) if side == 'team_a' else getattr(self, 'team_a', []),
                combat_time=time,
                event_callback=event_callback
            )
            skill_events = skill_executor.execute_skill(new_skill, ctx)
            if event_callback and skill_events:
                for event_type, event_data in skill_events:
                    if isinstance(event_data, dict):
                        merged = {'type': event_type}
                        merged.update(event_data)
                        if 'timestamp' not in merged:
                            merged['timestamp'] = merged.get('timestamp', time)
                        event_callback(event_type, merged)
                    else:
                        event_callback(event_type, {'type': event_type, 'data': event_data, 'timestamp': time})
            return None

