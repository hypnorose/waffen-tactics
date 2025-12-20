"""
Combat effect processor - handles trait effects, buffs, and death triggers
"""
import random
from typing import List, Dict, Any, Callable, Optional
from .effect_processor import EffectProcessor
from .event_canonicalizer import (
    emit_stat_buff,
    emit_regen_gain,
    emit_heal,
    emit_unit_died,
    emit_unit_heal,
    emit_gold_reward,
)


class CombatEffectProcessor:
    """Handles combat effects, buffs, and death triggers"""

    def __init__(self):
        self.effect_processor = EffectProcessor()

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
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ):
        """Process effects when a unit dies."""
        target = defending_team[target_idx]
        defending_side = 'team_a' if side == 'team_b' else 'team_b'

        try:
            print(f"[ENTER _process_unit_death] killer={getattr(killer,'id',None)} target={getattr(target,'id',None)} event_callback_set={event_callback is not None}")
        except Exception:
            pass

        # Prevent duplicate processing for the same death within a simulation tick
        if getattr(target, '_death_processed', False):
            return
        target._death_processed = True

        # Increment collected stats for the killer if they have relevant effects
        if killer:
            # Find all collect_stat values from kill_buff effects
            collect_stats = set()
            for eff in getattr(killer, 'effects', []):
                if eff.get('type') == 'on_enemy_death':
                    for action in eff.get('actions', []):
                        if action.get('type') == 'kill_buff':
                            collect_stat = action.get('collect_stat', 'defense')
                            collect_stats.add(collect_stat)
            
            if collect_stats:
                # Initialize collected_stats if needed
                if not hasattr(killer, 'collected_stats'):
                    killer.collected_stats = {}
                
                # Always collect kills
                killer.collected_stats['kills'] = killer.collected_stats.get('kills', 0) + 1
                
                # Collect specified stats from target
                for stat in collect_stats:
                    if stat != 'kills':  # kills is handled separately
                        value = getattr(target, stat, 0)
                        killer.collected_stats[stat] = killer.collected_stats.get(stat, 0) + value

                # Apply persistent buffs based on collected stats
                # For each kill, apply buffs (this is a simple implementation)
                # In a real game, this might be more complex based on traits
                # For now, buffs are applied through trait effects, not hardcoded here

        # Capture pre-death HP from authoritative list (prefer simulator-level lists)
        pre_hp = None
        try:
            # If simulator maintains global lists, prefer them for authoritative HP
            if hasattr(self, 'team_a') and hasattr(self, 'team_b') and hasattr(self, 'a_hp') and hasattr(self, 'b_hp'):
                if target in getattr(self, 'team_a', []):
                    idx = self.team_a.index(target)
                    pre_hp = int(self.a_hp[idx])
                elif target in getattr(self, 'team_b', []):
                    idx = self.team_b.index(target)
                    pre_hp = int(self.b_hp[idx])
                else:
                    pre_hp = int(defending_hp[target_idx])
            else:
                pre_hp = int(defending_hp[target_idx])
        except Exception:
            try:
                pre_hp = int(getattr(target, 'hp', None))
            except Exception:
                pre_hp = None

        # Ensure the authoritative HP list reflects the death BEFORE emitting
        # the canonical `unit_died` event to avoid snapshot/timing mismatch.
        try:
            # If we can map this target to the simulator-level HP lists, update those
            if hasattr(self, 'team_a') and hasattr(self, 'team_b') and hasattr(self, 'a_hp') and hasattr(self, 'b_hp'):
                if target in getattr(self, 'team_a', []):
                    idx = self.team_a.index(target)
                    old_hp_idx = int(self.a_hp[idx])
                    self.a_hp[idx] = 0
                    # print(f"[HP DEBUG] ts={time:.9f} side=team_a target={self.team_a[idx].id}:{self.team_a[idx].name} old_hp={old_hp_idx} -> new_hp=0 cause=unit_death (effect_processor)")
                elif target in getattr(self, 'team_b', []):
                    idx = self.team_b.index(target)
                    old_hp_idx_b = int(self.b_hp[idx])
                    self.b_hp[idx] = 0
                    # print(f"[HP DEBUG] ts={time:.9f} side=team_b target={self.team_b[idx].id}:{self.team_b[idx].name} old_hp={old_hp_idx_b} -> new_hp=0 cause=unit_death (effect_processor)")
                else:
                    old_def_hp = int(defending_hp[target_idx])
                    defending_hp[target_idx] = 0
                    # print(f"[HP DEBUG] ts={time:.9f} side={side} target={defending_team[target_idx].id}:{defending_team[target_idx].name} old_hp={old_def_hp} -> new_hp=0 cause=unit_death (effect_processor)")
            else:
                old_def_hp2 = int(defending_hp[target_idx])
                defending_hp[target_idx] = 0
                # print(f"[HP DEBUG] ts={time:.9f} side={side} target={defending_team[target_idx].id}:{defending_team[target_idx].name} old_hp={old_def_hp2} -> new_hp=0 cause=unit_death (effect_processor)")
        except Exception:
            try:
                defending_hp[target_idx] = 0
            except Exception:
                pass

        # Keep the CombatUnit object in sync via canonical emitter
        # Determine the actual side of the dead unit from simulator lists
        target_side = None
        try:
            if hasattr(self, 'team_a') and target in getattr(self, 'team_a', []):
                target_side = 'team_a'
            elif hasattr(self, 'team_b') and target in getattr(self, 'team_b', []):
                target_side = 'team_b'
        except Exception:
            target_side = None

        # Fallback to defending_side if we couldn't determine membership
        if target_side is None:
            target_side = defending_side

        # Use canonical emitter to mark unit as dead and update in-memory HP.
        # Call emitter regardless of presence of event_callback so in-memory
        # state is normalized even when no callback is provided.
        try:
            emit_unit_died(event_callback, target, side=target_side, timestamp=time, unit_hp=pre_hp)
        except Exception:
            pass

        try:
            print(f"[DEATH DEBUG] emitted unit_died for {getattr(target,'id',None)}; attacking_team_len={len(attacking_team) if attacking_team is not None else 'None'}; attacking_ids={[getattr(u,'id',None) for u in (attacking_team or [])]}")
        except Exception:
            pass

        # Ensure on_enemy_death stat effects are applied even if prior logic skipped them
        try:
            for unit in (attacking_team or []):
                for eff in getattr(unit, 'effects', []):
                    if eff.get('type') == 'on_enemy_death':
                        try:
                            self._apply_stat_buff(unit, eff, attacking_hp, (attacking_team or []).index(unit), time, log, event_callback, side, attacking_team, defending_team, attacking_hp, defending_hp)
                        except Exception:
                            pass
        except Exception:
            pass

        # Trigger on_enemy_death effects for attacking team
        print(f"[DEATH LOOP] attacking_team_len={len(attacking_team) if attacking_team is not None else 'None'}")
        for idx_unit, unit in enumerate(attacking_team or []):
            try:
                print(f"[DEATH LOOP] idx={idx_unit} unit_id={getattr(unit,'id',None)} effects={getattr(unit,'effects',None)}")
            except Exception:
                pass
            for eff in getattr(unit, 'effects', []):
                if eff.get('type') == 'on_enemy_death':
                    try:
                        print(f"[DEATH LOOP] applying on_enemy_death for unit={getattr(unit,'id',None)} eff={eff}")
                    except Exception:
                        pass
                    actions = eff.get('actions', [])
                    if actions:
                        self._apply_actions(unit, actions, attacking_hp, attacking_team.index(unit), time, log, event_callback, side, attacking_team, attacking_hp, defending_team, defending_hp)
                    else:
                        # Backward compatibility
                        if 'reward' in eff:
                            self._apply_reward(unit, eff, attacking_hp, attacking_team.index(unit), time, log, event_callback, side, attacking_team, attacking_hp)
                        self._apply_stat_buff(unit, eff, attacking_hp, attacking_team.index(unit), time, log, event_callback, side, attacking_team, defending_team, attacking_hp, defending_hp)

        # Trigger on_ally_death effects for surviving allies on defending team
        triggered_rewards = set()  # Track which reward types have been triggered for this death
        for i, unit in enumerate(defending_team):
            if defending_hp[i] <= 0:
                continue
            for eff in getattr(unit, 'effects', []):
                if eff.get('type') == 'on_ally_death':
                    actions = eff.get('actions', [])
                    if actions:
                        self._apply_actions(unit, actions, defending_hp, i, time, log, event_callback, defending_side, attacking_team, attacking_hp, defending_team, defending_hp, triggered_rewards, eff)
                    else:
                        # Backward compatibility
                        if 'reward' in eff:
                            reward_type = eff.get('reward')
                            if eff.get('trigger_once', False):
                                if reward_type in triggered_rewards:
                                    continue
                                triggered_rewards.add(reward_type)
                            self._apply_reward(unit, eff, defending_hp, i, time, log, event_callback, defending_side)
                        self._apply_stat_buff(unit, eff, defending_hp, i, time, log, event_callback, defending_side, attacking_team, defending_team, attacking_hp, defending_hp)

        # Note: stat_steal effects have been replaced with on_enemy_death + permanent_stat_buff

    def _apply_reward(
        self,
        unit: 'CombatUnit',
        effect: Dict[str, Any],
        hp_list: List[int],
        unit_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str,
        attacking_team: Optional[List['CombatUnit']] = None,
        attacking_hp: Optional[List[int]] = None
    ):
        """Apply reward from an effect."""
        chance = effect.get('chance', 100)
        if random.randint(1, 100) > chance:
            return
        reward = effect.get('reward')
        target = effect.get('target', 'self')
        if reward == 'gold':
            amount = int(effect.get('value', 0))
            if target == 'self':
                log.append(f"{unit.name} gains +{amount} gold")
                if event_callback:
                    emit_gold_reward(event_callback, unit, amount, side=side, timestamp=time)
            elif target == 'team' and attacking_team and attacking_hp:
                # For team, distribute or just log as team reward
                log.append(f"Team gains +{amount} gold")
                if event_callback:
                    emit_gold_reward(event_callback, unit, amount, side=side, timestamp=time)
        elif reward == 'hp_regen':
            is_pct = effect.get('is_percentage', False)
            val = float(effect.get('value', 0))
            duration = float(effect.get('duration', 5.0))
            if duration <= 0:
                duration = 5.0
            if is_pct:
                total_amount = unit.max_hp * (val / 100.0)
            else:
                total_amount = float(val)
            add_per_sec = total_amount / duration
            if add_per_sec > 0:
                if target == 'self':
                    unit.hp_regen_per_sec += add_per_sec
                    log.append(f"[{time:.2f}s] {unit.name} gains +{total_amount:.2f} HP over {duration}s (+{add_per_sec:.2f} HP/s)")
                    if event_callback:
                        emit_regen_gain(event_callback, unit, add_per_sec, total_amount=total_amount, duration=duration, side=side, timestamp=time)
                elif target == 'team' and attacking_team and attacking_hp:
                    # Apply to all surviving units in attacking team
                    survivors = [u for u, hp in zip(attacking_team, attacking_hp) if hp > 0]
                    if survivors:
                        per_unit = add_per_sec / len(survivors)
                        for u in survivors:
                            u.hp_regen_per_sec += per_unit
                        log.append(f"[{time:.2f}s] Team gains +{total_amount:.2f} HP over {duration}s (+{add_per_sec:.2f} HP/s total)")
                        if event_callback:
                            emit_regen_gain(event_callback, unit, add_per_sec, total_amount=total_amount, duration=duration, side=side, target='team', timestamp=time)

    def _apply_actions(
        self,
        unit: 'CombatUnit',
        actions: List[Dict[str, Any]],
        hp_list: List[int],
        unit_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str,
        attacking_team: Optional[List['CombatUnit']] = None,
        attacking_hp: Optional[List[int]] = None,
        defending_team: Optional[List['CombatUnit']] = None,
        defending_hp: Optional[List[int]] = None,
        triggered_rewards: Optional[set] = None,
        effect: Optional[Dict[str, Any]] = None
    ):
        """Apply list of actions from an effect."""
        try:
            print(f"[APPLY_ACTIONS] unit={getattr(unit,'id',None)} actions={actions} event_callback_set={event_callback is not None}")
        except Exception:
            pass
        for action in actions:
            action_type = action.get('type')
            try:
                print(f"[APPLY_ACTIONS] action_type={action_type} action={action}")
            except Exception:
                pass
            if action_type == 'stat_buff':
                self._apply_stat_buff(unit, action, hp_list, unit_idx, time, log, event_callback, side, attacking_team, defending_team, attacking_hp, defending_hp)
            elif action_type in ('kill_buff', 'collect_stat'):
                # Apply permanent stat buff from kill
                stat = action.get('stat')
                value = action.get('value', 0)
                is_percentage = action.get('is_percentage', False)
                
                # Initialize permanent_buffs_applied if needed
                if not hasattr(unit, 'permanent_buffs_applied'):
                    unit.permanent_buffs_applied = {}
                
                if stat == 'defense':
                    if is_percentage:
                        added = int(unit.defense * (value / 100.0))
                        unit.defense += added
                    else:
                        added = int(value)
                        unit.defense += added
                    log.append(f"{unit.name} gains permanent +{added} Defense from kill")
                    unit.permanent_buffs_applied['defense'] = unit.permanent_buffs_applied.get('defense', 0) + added
                    if event_callback:
                        emit_stat_buff(event_callback, unit, 'defense', added, value_type='percentage' if is_percentage else 'flat', duration=None, permanent=True, source=None, side=side, timestamp=time, cause='kill')
                elif stat == 'attack':
                    if is_percentage:
                        added = int(unit.attack * (value / 100.0))
                        unit.attack += added
                    else:
                        added = int(value)
                        unit.attack += added
                    log.append(f"{unit.name} gains permanent +{added} Attack from kill")
                    unit.permanent_buffs_applied['attack'] = unit.permanent_buffs_applied.get('attack', 0) + added
                    if event_callback:
                        emit_stat_buff(event_callback, unit, 'attack', added, value_type='percentage' if is_percentage else 'flat', duration=None, permanent=True, source=None, side=side, timestamp=time, cause='kill')
                elif stat == 'hp':
                    if is_percentage:
                        added = int(unit.max_hp * (value / 100.0))
                        # For HP, we need to update both max_hp and current hp
                        unit.max_hp += added
                        # Also update the hp_list
                        hp_list[unit_idx] += added
                    else:
                        added = int(value)
                        unit.max_hp += added
                        hp_list[unit_idx] += added
                    log.append(f"{unit.name} gains permanent +{added} Max HP from kill")
                    unit.permanent_buffs_applied['hp'] = unit.permanent_buffs_applied.get('hp', 0) + added
                    if event_callback:
                        emit_stat_buff(event_callback, unit, 'hp', added, value_type='percentage' if is_percentage else 'flat', duration=None, permanent=True, source=None, side=side, timestamp=time, cause='kill')
                # Add other stats as needed
            elif action_type == 'reward':
                if triggered_rewards is not None and effect and effect.get('trigger_once', False):
                    reward_type = action.get('reward')
                    if reward_type in triggered_rewards:
                        continue
                    triggered_rewards.add(reward_type)
                self._apply_reward(unit, action, hp_list, unit_idx, time, log, event_callback, side, attacking_team, attacking_hp)

    def _apply_stat_buff_with_handlers(
        self,
        unit: 'CombatUnit',
        effect: Dict[str, Any],
        hp_list: List[int],
        unit_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str,
        attacking_team: Optional[List['CombatUnit']] = None,
        defending_team: Optional[List['CombatUnit']] = None,
        attacking_hp: Optional[List[int]] = None,
        defending_hp: Optional[List[int]] = None
    ):
        """Apply stat buff using the new StatBuffHandlers."""
        stats = effect.get('stats', [])
        val = effect.get('value', 0)
        buff_type = 'percentage' if effect.get('is_percentage', False) else 'flat'
        target = effect.get('target', 'self')
        only_same_trait = effect.get('only_same_trait', False)

        # Find recipients
        recipients = self.effect_processor.recipient_resolver.find_recipients(
            unit, target, only_same_trait, attacking_team, defending_team, side
        )

        if not recipients:
            return

        for stat_type in stats:
            if stat_type not in self.effect_processor.buff_handlers:
                log.append(f"Unknown stat type: {stat_type}")
                continue

            handler = self.effect_processor.buff_handlers[stat_type]

            for recipient in recipients:
                # Calculate buff increment with amplifiers
                base_increment = self.effect_processor.stat_calculator.calculate_buff_increment(
                    0, val, buff_type, getattr(unit, stat_type, 0) if buff_type == 'percentage' else None
                )

                # Apply buff amplifier from source
                mult = 1.0
                for beff in getattr(unit, 'effects', []):
                    if beff.get('type') == 'buff_amplifier':
                        mult = max(mult, float(beff.get('multiplier', 1)))

                # Apply recipient-specific amplifier
                recipient_mult = 1.0
                for beff in getattr(recipient, 'effects', []):
                    if beff.get('type') == 'buff_amplifier':
                        recipient_mult = max(recipient_mult, float(beff.get('multiplier', 1)))

                final_increment = base_increment * mult * recipient_mult

                # Find recipient index in appropriate team
                recipient_idx = -1
                if side == 'team_a' and attacking_team:
                    try:
                        recipient_idx = attacking_team.index(recipient)
                    except ValueError:
                        pass
                elif side == 'team_b' and defending_team:
                    try:
                        recipient_idx = defending_team.index(recipient)
                    except ValueError:
                        pass

                # Apply buff using handler
                handler.apply_buff(
                    recipient, 
                    final_increment, 
                    buff_type == 'percentage', 
                    1.0,  # amplifier already applied to final_increment
                    hp_list, 
                    recipient_idx, 
                    time, 
                    log, 
                    event_callback, 
                    side
                )

                # Handler already emits events/logs; avoid duplicate event emission here

    def _apply_stat_buff(
        self,
        unit: 'CombatUnit',
        effect: Dict[str, Any],
        hp_list: List[int],
        unit_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str,
        attacking_team: Optional[List['CombatUnit']] = None,
        defending_team: Optional[List['CombatUnit']] = None,
        attacking_hp: Optional[List[int]] = None,
        defending_hp: Optional[List[int]] = None
    ):
        """Apply stat buff from an effect."""
        try:
            print(f"[STAT_APPLY] unit={getattr(unit,'id',None)} effect={effect}")
        except Exception:
            pass
        # Try to use new handlers first for supported stats
        supported_stats = {'attack', 'defense', 'hp', 'attack_speed', 'mana_regen'}
        effect_stats = set(effect.get('stats', []))

        if effect_stats.issubset(supported_stats):
            # Use new handlers
            self._apply_stat_buff_with_handlers(
                unit, effect, hp_list, unit_idx, time, log, event_callback,
                side, attacking_team, defending_team, attacking_hp, defending_hp
            )
            return

        # Fallback to old implementation for unsupported stats
        stats = effect.get('stats', [])
        val = effect.get('value', 0)
        is_pct = effect.get('is_percentage', False)
        stats = effect.get('stats', [])
        val = effect.get('value', 0)
        is_pct = effect.get('is_percentage', False)
        for st in stats:
            if st == 'attack':
                if is_pct:
                    add = int(unit.attack * (val / 100.0))
                else:
                    add = int(val)
                # Apply buff amplifier if target has such an effect
                mult = 1.0
                for beff in getattr(unit, 'effects', []):
                    if beff.get('type') == 'buff_amplifier':
                        mult = max(mult, float(beff.get('multiplier', 1)))
                add = int(add * mult)
                # Decide recipients based on effect target
                target = effect.get('target', 'self')
                only_same_trait = effect.get('only_same_trait', False)

                def apply_to_recipient(recipient):
                    mult = 1.0
                    for beff in getattr(recipient, 'effects', []):
                        if beff.get('type') == 'buff_amplifier':
                            mult = max(mult, float(beff.get('multiplier', 1)))
                    added = int(add * mult)
                    recipient.attack += added
                    log.append(f"{recipient.name} gains +{added} Atak (stat_buff)")
                    # Emit canonical stat_buff and ensure recipient state reflects the buff
                    if event_callback:
                        emit_stat_buff(event_callback, recipient, 'attack', added, value_type='flat', duration=None, permanent=False, source=unit, side=side, timestamp=time, cause='effect')

                if target == 'self':
                    apply_to_recipient(unit)
                else:
                    recipients = []
                    if target == 'team' and attacking_team is not None and side == 'team_a':
                        recipients = [u for u in attacking_team if getattr(u, 'hp', 0) > 0]
                    elif target == 'team' and defending_team is not None and side == 'team_b':
                        recipients = [u for u in defending_team if getattr(u, 'hp', 0) > 0]
                    elif target == 'board':
                        recipients = []
                        if attacking_team:
                            recipients += [u for u in attacking_team if getattr(u, 'hp', 0) > 0]
                        if defending_team:
                            recipients += [u for u in defending_team if getattr(u, 'hp', 0) > 0]
                    else:
                        # Unknown/unsupported target - fallback to self
                        apply_to_recipient(unit)

                    if only_same_trait:
                        # filter recipients to those that share at least one faction/class with source unit
                        src_traits = set(getattr(unit, 'factions', []) + getattr(unit, 'classes', []))
                        recipients = [r for r in recipients if src_traits.intersection(set(getattr(r, 'factions', []) + getattr(r, 'classes', [])))]

                    for r in recipients:
                        apply_to_recipient(r)
            elif st in ('defense', 'hp', 'attack_speed', 'mana_regen', 'lifesteal', 'damage_reduction', 'hp_regen_per_sec'):
                # Calculate base add using the source unit as before
                if st == 'defense':
                    if is_pct:
                        base_add = int(unit.defense * (val / 100.0))
                    else:
                        base_add = int(val)
                elif st == 'hp':
                    if is_pct:
                        base_add = int(unit.max_hp * (val / 100.0))
                    else:
                        base_add = int(val)
                elif st == 'attack_speed':
                    if is_pct:
                        base_add = unit.attack_speed * (val / 100.0)
                    else:
                        base_add = float(val)
                elif st == 'mana_regen':
                    if is_pct:
                        base_add = int(unit.mana_regen * (val / 100.0))
                    else:
                        base_add = int(val)
                elif st == 'lifesteal':
                    if is_pct:
                        base_add = val / 100.0
                    else:
                        base_add = float(val)
                elif st == 'damage_reduction':
                    if is_pct:
                        base_add = val / 100.0
                    else:
                        base_add = float(val)
                elif st == 'hp_regen_per_sec':
                    if is_pct:
                        base_add = unit.max_hp * (val / 100.0)
                    else:
                        base_add = float(val)

                # buff amplifier on source does not necessarily apply to recipients,
                # recipients may have their own amplifiers; we will multiply per-recipient
                target = effect.get('target', 'self')
                only_same_trait = effect.get('only_same_trait', False)

                def apply_stat_to(recipient, rec_hp_list=None):
                    # compute recipient-local add (for percentage-ish stats we keep base_add as computed)
                    mult = 1.0
                    for beff in getattr(recipient, 'effects', []):
                        if beff.get('type') == 'buff_amplifier':
                            mult = max(mult, float(beff.get('multiplier', 1)))
                    added = base_add * mult
                    if st in ('defense', 'mana_regen'):
                        added_int = int(added)
                        if st == 'defense':
                            recipient.defense += added_int
                        else:
                            recipient.mana_regen += added_int
                        log.append(f"{recipient.name} gains +{added_int} {st} (stat_buff)")
                        if event_callback:
                            emit_stat_buff(event_callback, recipient, st, added_int, value_type='flat', duration=None, permanent=False, source=unit, side=side, timestamp=time, cause='effect')
                    elif st == 'hp':
                        added_int = int(added)
                        # find recipient index in hp lists
                        if attacking_team and recipient in attacking_team and attacking_hp is not None:
                            idx = attacking_team.index(recipient)
                            old_hp = attacking_hp[idx]
                            attacking_hp[idx] = min(recipient.max_hp, attacking_hp[idx] + added_int)
                            log.append(f"{recipient.name} heals +{added_int} HP (stat_buff)")
                            if event_callback:
                                # Pass old HP so emit_heal can calculate correct new HP
                                emit_heal(event_callback, recipient, added_int, source=unit, side='team_a' if recipient in (attacking_team or []) else 'team_b', timestamp=time, current_hp=old_hp)
                        elif defending_team and recipient in defending_team and defending_hp is not None:
                            idx = defending_team.index(recipient)
                            old_hp = defending_hp[idx]
                            defending_hp[idx] = min(recipient.max_hp, defending_hp[idx] + added_int)
                            log.append(f"{recipient.name} heals +{added_int} HP (stat_buff)")
                            if event_callback:
                                # Pass old HP so emit_heal can calculate correct new HP
                                emit_heal(event_callback, recipient, added_int, source=unit, side='team_b' if recipient in (defending_team or []) else 'team_a', timestamp=time, current_hp=old_hp)
                    elif st == 'attack_speed':
                        recipient.attack_speed += float(added)
                        log.append(f"{recipient.name} gains +{added:.2f} Attack Speed (stat_buff)")
                        if event_callback:
                            emit_stat_buff(event_callback, recipient, 'attack_speed', added, value_type='flat', duration=None, permanent=False, source=unit, side=side, timestamp=time, cause='effect')
                    elif st == 'lifesteal':
                        recipient.lifesteal += float(added)
                        log.append(f"{recipient.name} gains +{float(added):.1%} Lifesteal (stat_buff)")
                        if event_callback:
                            emit_stat_buff(event_callback, recipient, 'lifesteal', added, value_type='flat', duration=None, permanent=False, source=unit, side=side, timestamp=time, cause='effect')
                    elif st == 'damage_reduction':
                        recipient.damage_reduction += float(added)
                        log.append(f"{recipient.name} gains +{float(added):.1%} Damage Reduction (stat_buff)")
                        if event_callback:
                            emit_stat_buff(event_callback, recipient, 'damage_reduction', added, value_type='flat', duration=None, permanent=False, source=unit, side=side, timestamp=time, cause='effect')
                    elif st == 'hp_regen_per_sec':
                        recipient.hp_regen_per_sec += float(added)
                        log.append(f"{recipient.name} gains +{float(added):.2f} HP Regen/sec (stat_buff)")
                        if event_callback:
                            emit_regen_gain(event_callback, recipient, added, side=side, timestamp=time)

                # Apply according to target
                if target == 'self':
                    apply_stat_to(unit, hp_list)
                else:
                    recipients = []
                    if target == 'team':
                        # choose team matching the side where the trigger happened
                        if side == 'team_a' and attacking_team:
                            recipients = [u for u in attacking_team if getattr(u, 'hp', 0) > 0]
                        elif side == 'team_b' and defending_team:
                            recipients = [u for u in defending_team if getattr(u, 'hp', 0) > 0]
                    elif target == 'board':
                        if attacking_team:
                            recipients += [u for u in attacking_team if getattr(u, 'hp', 0) > 0]
                        if defending_team:
                            recipients += [u for u in defending_team if getattr(u, 'hp', 0) > 0]
                    else:
                        # unsupported target: fallback to self
                        recipients = [unit]

                    if only_same_trait:
                        src_traits = set(getattr(unit, 'factions', []) + getattr(unit, 'classes', []))
                        recipients = [r for r in recipients if src_traits.intersection(set(getattr(r, 'factions', []) + getattr(r, 'classes', [])))]

                    for r in recipients:
                        apply_stat_to(r)

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
                        old_hp = hp_list[target_idx]
                        hp_list[target_idx] = min(team[target_idx].max_hp, hp_list[target_idx] + heal_amt)
                        log.append(f"{unit.name} heals {team[target_idx].name} for {heal_amt} (ally hp below {thresh}%)")
                        if event_callback:
                            emit_heal(event_callback, team[target_idx], heal_amt, source=None, side=side, timestamp=time, current_hp=old_hp)
                        eff['_triggered'] = True
                        break

    def _process_per_round_buffs(
        self,
        team_a: List['CombatUnit'],
        team_b: List['CombatUnit'],
        a_hp: List[int],
        b_hp: List[int],
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        round_number: int
    ):
        """Apply per-round buffs for both teams based on current round number."""
        # Team A buffs
        for idx_u, u in enumerate(team_a):
            for eff in getattr(u, 'effects', []):
                if eff.get('type') == 'per_round_buff':
                    stat = eff.get('stat')
                    val = eff.get('value', 0)
                    is_pct = eff.get('is_percentage', False)
                    
                    # Calculate buff based on round number
                    buff_amount = val * round_number
                    
                    if stat == 'hp':
                        if is_pct:
                            add = int(u.max_hp * (buff_amount / 100.0))
                        else:
                            add = int(buff_amount)
                        old_hp = a_hp[idx_u]
                        a_hp[idx_u] = min(u.max_hp, a_hp[idx_u] + add)
                        log.append(f"{u.name} +{add} HP (per round buff)")
                        if event_callback and add > 0:
                            emit_heal(event_callback, u, add, source=None, side='team_a', timestamp=time, current_hp=old_hp)

        # Team B buffs
        for idx_u, u in enumerate(team_b):
            for eff in getattr(u, 'effects', []):
                if eff.get('type') == 'per_round_buff':
                    stat = eff.get('stat')
                    val = eff.get('value', 0)
                    is_pct = eff.get('is_percentage', False)

                    # Calculate buff based on round number
                    buff_amount = val * round_number

                    if stat == 'hp':
                        if is_pct:
                            add = int(u.max_hp * (buff_amount / 100.0))
                        else:
                            add = int(buff_amount)
                        old_hp = b_hp[idx_u]
                        b_hp[idx_u] = min(u.max_hp, b_hp[idx_u] + add)
                        log.append(f"{u.name} +{add} HP (per round buff)")
                        if event_callback and add > 0:
                            emit_heal(event_callback, u, add, source=None, side='team_b', timestamp=time, current_hp=old_hp)