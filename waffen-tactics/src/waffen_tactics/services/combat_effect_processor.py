"""
Combat effect processor - handles trait effects, buffs, and death triggers
"""
import random
from typing import List, Dict, Any, Callable, Optional
from .effect_processor import EffectProcessor


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

        if event_callback:
            event_callback('unit_died', {
                'unit_id': target.id,
                'unit_name': target.name,
                'side': defending_side,
                'timestamp': time
            })

        # Trigger on_enemy_death effects for attacking team
        for unit in attacking_team:
            for eff in getattr(unit, 'effects', []):
                if eff.get('type') == 'on_enemy_death':
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
                    event_callback('gold_reward', {
                        'amount': amount,
                        'unit_id': unit.id,
                        'unit_name': unit.name,
                        'side': side,
                        'timestamp': time
                    })
            elif target == 'team' and attacking_team and attacking_hp:
                # For team, distribute or just log as team reward
                log.append(f"Team gains +{amount} gold")
                if event_callback:
                    event_callback('gold_reward', {
                        'amount': amount,
                        'unit_id': unit.id,
                        'unit_name': unit.name,
                        'side': side,
                        'timestamp': time,
                        'target': 'team'
                    })
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
                            event_callback('regen_gain', {
                                'unit_id': unit.id,
                                'unit_name': unit.name,
                                'amount_per_sec': add_per_sec,
                                'total_amount': total_amount,
                                'duration': duration,
                                'side': side,
                                'timestamp': time
                            })
                elif target == 'team' and attacking_team and attacking_hp:
                    # Apply to all surviving units in attacking team
                    survivors = [u for u, hp in zip(attacking_team, attacking_hp) if hp > 0]
                    if survivors:
                        per_unit = add_per_sec / len(survivors)
                        for u in survivors:
                            u.hp_regen_per_sec += per_unit
                        log.append(f"[{time:.2f}s] Team gains +{total_amount:.2f} HP over {duration}s (+{add_per_sec:.2f} HP/s total)")
                        if event_callback:
                                event_callback('regen_gain', {
                                    'unit_id': unit.id,
                                    'unit_name': unit.name,
                                    'amount_per_sec': add_per_sec,
                                    'total_amount': total_amount,
                                    'duration': duration,
                                    'side': side,
                                    'target': 'team',
                                    'timestamp': time
                                })

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
        for action in actions:
            action_type = action.get('type')
            if action_type == 'stat_buff':
                self._apply_stat_buff(unit, action, hp_list, unit_idx, time, log, event_callback, side, attacking_team, defending_team, attacking_hp, defending_hp)
            elif action_type in ('kill_buff', 'collect_stat'):
                # Use new EffectProcessor for kill_buff and collect_stat actions
                result = self.effect_processor.process_effect(
                    action, unit, attacking_team, defending_team,
                    attacking_hp, defending_hp, side
                )
                if result.get('errors'):
                    for error in result['errors']:
                        log.append(f"Effect processing error: {error}")
                if result.get('processed') and result.get('changes'):
                    # Log successful processing
                    if 'buffs_applied' in result['changes']:
                        for buff_info in result['changes']['buffs_applied']:
                            log.append(f"{unit.name} applied {buff_info['stat_type']} buff (+{buff_info['increment']})")
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

                # Log and event
                log.append(f"{recipient.name} gains +{final_increment} {stat_type} (stat_buff)")
                if event_callback:
                    event_callback('stat_buff', {
                        'unit_id': recipient.id,
                        'unit_name': recipient.name,
                        'stat': stat_type,
                        'amount': final_increment,
                        'side': side,
                        'timestamp': time
                    })

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
                    if event_callback:
                        event_callback('stat_buff', {
                            'unit_id': recipient.id,
                            'unit_name': recipient.name,
                            'stat': 'attack',
                            'amount': added,
                            'side': side,
                            'timestamp': time
                        })

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
                            event_callback('stat_buff', {'unit_id': recipient.id, 'unit_name': recipient.name, 'stat': st, 'amount': added_int, 'side': side, 'timestamp': time})
                    elif st == 'hp':
                        added_int = int(added)
                        # find recipient index in hp lists
                        if attacking_team and recipient in attacking_team and attacking_hp is not None:
                            idx = attacking_team.index(recipient)
                            attacking_hp[idx] = min(recipient.max_hp, attacking_hp[idx] + added_int)
                            log.append(f"{recipient.name} heals +{added_int} HP (stat_buff)")
                            if event_callback:
                                event_callback('heal', {'unit_id': recipient.id, 'unit_name': recipient.name, 'amount': added_int, 'side': 'team_a' if recipient in (attacking_team or []) else 'team_b', 'unit_hp': attacking_hp[idx] if recipient in attacking_team else None, 'unit_max_hp': recipient.max_hp, 'timestamp': time})
                        elif defending_team and recipient in defending_team and defending_hp is not None:
                            idx = defending_team.index(recipient)
                            defending_hp[idx] = min(recipient.max_hp, defending_hp[idx] + added_int)
                            log.append(f"{recipient.name} heals +{added_int} HP (stat_buff)")
                            if event_callback:
                                event_callback('heal', {'unit_id': recipient.id, 'unit_name': recipient.name, 'amount': added_int, 'side': 'team_b' if recipient in (defending_team or []) else 'team_a', 'unit_hp': defending_hp[idx] if recipient in defending_team else None, 'unit_max_hp': recipient.max_hp, 'timestamp': time})
                    elif st == 'attack_speed':
                        recipient.attack_speed += float(added)
                        log.append(f"{recipient.name} gains +{added:.2f} Attack Speed (stat_buff)")
                        if event_callback:
                            event_callback('stat_buff', {'unit_id': recipient.id, 'unit_name': recipient.name, 'stat': 'attack_speed', 'amount': added, 'side': side, 'timestamp': time})
                    elif st == 'lifesteal':
                        recipient.lifesteal += float(added)
                        log.append(f"{recipient.name} gains +{float(added):.1%} Lifesteal (stat_buff)")
                        if event_callback:
                            event_callback('stat_buff', {'unit_id': recipient.id, 'unit_name': recipient.name, 'stat': 'lifesteal', 'amount': added, 'side': side, 'timestamp': time})
                    elif st == 'damage_reduction':
                        recipient.damage_reduction += float(added)
                        log.append(f"{recipient.name} gains +{float(added):.1%} Damage Reduction (stat_buff)")
                        if event_callback:
                            event_callback('stat_buff', {'unit_id': recipient.id, 'unit_name': recipient.name, 'stat': 'damage_reduction', 'amount': added, 'side': side, 'timestamp': time})
                    elif st == 'hp_regen_per_sec':
                        recipient.hp_regen_per_sec += float(added)
                        log.append(f"{recipient.name} gains +{float(added):.2f} HP Regen/sec (stat_buff)")
                        if event_callback:
                            event_callback('regen_gain', {'unit_id': recipient.id, 'unit_name': recipient.name, 'amount_per_sec': added, 'side': side, 'timestamp': time})

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

    def _process_per_round_buffs(
        self,
        team_a: List['CombatUnit'],
        team_b: List['CombatUnit'],
        a_hp: List[int],
        b_hp: List[int],
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]]
    ):
        """Apply per-round buffs for both teams."""
        # Team A buffs
        for idx_u, u in enumerate(team_a):
            for eff in getattr(u, 'effects', []):
                if eff.get('type') == 'per_second_buff':
                    stat = eff.get('stat')
                    val = eff.get('value', 0)
                    is_pct = eff.get('is_percentage', False)
                    # Check for buff amplifier on this unit
                    mult = 1.0
                    for beff in getattr(u, 'effects', []):
                        if beff.get('type') == 'buff_amplifier':
                            try:
                                mult = max(mult, float(beff.get('multiplier', 1)))
                            except Exception:
                                pass
                    if stat == 'attack':
                        if is_pct:
                            add = int(u.attack * (val / 100.0) * mult)
                        else:
                            add = int(val * mult)
                        u.attack += add
                        log.append(f"{u.name} +{add} Atak (per second)")
                    if stat == 'hp':
                        if is_pct:
                            add = int(u.max_hp * (val / 100.0) * mult)
                        else:
                            add = int(val * mult)
                        a_hp[idx_u] = min(u.max_hp, a_hp[idx_u] + add)
                        log.append(f"{u.name} +{add} HP (per second)")
                        if event_callback and add > 0:
                            event_callback('heal', {
                                'unit_id': u.id,
                                'unit_name': u.name,
                                'amount': add,
                                'side': 'team_a',
                                'unit_hp': a_hp[idx_u],
                                'unit_max_hp': u.max_hp,
                                'timestamp': time
                            })

        # Team B buffs
        for idx_u, u in enumerate(team_b):
            for eff in getattr(u, 'effects', []):
                if eff.get('type') == 'per_second_buff':
                    stat = eff.get('stat')
                    val = eff.get('value', 0)
                    is_pct = eff.get('is_percentage', False)
                    # Check for buff amplifier on this unit
                    mult_b = 1.0
                    for beff2 in getattr(u, 'effects', []):
                        if beff2.get('type') == 'buff_amplifier':
                            try:
                                mult_b = max(mult_b, float(beff2.get('multiplier', 1)))
                            except Exception:
                                pass
                    if stat == 'attack':
                        if is_pct:
                            add = int(u.attack * (val / 100.0) * mult_b)
                        else:
                            add = int(val * mult_b)
                        u.attack += add
                        log.append(f"{u.name} +{add} Atak (per second)")
                    if stat == 'hp':
                        if is_pct:
                            add = int(u.max_hp * (val / 100.0) * mult_b)
                        else:
                            add = int(val * mult_b)
                        b_hp[idx_u] = min(u.max_hp, b_hp[idx_u] + add)
                        log.append(f"{u.name} +{add} HP (per second)")
                        if event_callback and add > 0:
                            event_callback('heal', {
                                'unit_id': u.id,
                                'unit_name': u.name,
                                'amount': add,
                                'side': 'team_b',
                                'unit_hp': b_hp[idx_u],
                                'unit_max_hp': u.max_hp,
                                'timestamp': time
                            })

        # Apply base mana regen for all units
        for u in team_a + team_b:
            if u.mana_regen > 0:
                old_mana = u.mana
                u.mana = min(u.max_mana, u.mana + u.mana_regen)
                add = u.mana - old_mana
                if add > 0:
                    log.append(f"{u.name} +{add} Mana (regen)")
                    if event_callback:
                        event_callback('mana_update', {
                            'unit_id': u.id,
                            'unit_name': u.name,
                            'current_mana': u.mana,
                            'max_mana': u.max_mana,
                            'side': 'team_a' if u in team_a else 'team_b',
                            'timestamp': time
                        })