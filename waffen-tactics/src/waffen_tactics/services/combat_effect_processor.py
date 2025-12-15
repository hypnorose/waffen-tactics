"""
Combat effect processor - handles trait effects, buffs, and death triggers
"""
import random
from typing import List, Dict, Any, Callable, Optional


class CombatEffectProcessor:
    """Handles combat effects, buffs, and death triggers"""

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
                        self._apply_actions(unit, actions, attacking_hp, attacking_team.index(unit), time, log, event_callback, side, attacking_team, attacking_hp)
                    else:
                        # Backward compatibility
                        if 'reward' in eff:
                            self._apply_reward(unit, eff, attacking_hp, attacking_team.index(unit), time, log, event_callback, side, attacking_team, attacking_hp)
                        self._apply_stat_buff(unit, eff, attacking_hp, attacking_team.index(unit), time, log, event_callback, side)

        # Trigger on_ally_death effects for surviving allies on defending team
        triggered_rewards = set()  # Track which reward types have been triggered for this death
        for i, unit in enumerate(defending_team):
            if defending_hp[i] <= 0:
                continue
            for eff in getattr(unit, 'effects', []):
                if eff.get('type') == 'on_ally_death':
                    actions = eff.get('actions', [])
                    if actions:
                        self._apply_actions(unit, actions, defending_hp, i, time, log, event_callback, defending_side, None, None, triggered_rewards, eff)
                    else:
                        # Backward compatibility
                        if 'reward' in eff:
                            reward_type = eff.get('reward')
                            if eff.get('trigger_once', False):
                                if reward_type in triggered_rewards:
                                    continue
                                triggered_rewards.add(reward_type)
                            self._apply_reward(unit, eff, defending_hp, i, time, log, event_callback, defending_side)
                        self._apply_stat_buff(unit, eff, defending_hp, i, time, log, event_callback, defending_side)

        # Stat steal effects for attacking team
        for unit in attacking_team:
            for eff in getattr(unit, 'effects', []):
                if eff.get('type') == 'stat_steal':
                    stat = eff.get('stat')
                    value = eff.get('value', 0)  # percentage
                    is_pct = eff.get('is_percentage', True)
                    if stat and is_pct:
                        stolen_value = 0
                        if stat == 'defense':
                            stolen_value = int(target.defense * (value / 100.0))
                            unit.defense += stolen_value
                            log.append(f"{unit.name} steals +{stolen_value} Defense from {target.name}")

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
                            'side': side
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
                                'target': 'team'
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
        triggered_rewards: Optional[set] = None,
        effect: Optional[Dict[str, Any]] = None
    ):
        """Apply list of actions from an effect."""
        for action in actions:
            action_type = action.get('type')
            if action_type == 'stat_buff':
                self._apply_stat_buff(unit, action, hp_list, unit_idx, time, log, event_callback, side)
            elif action_type == 'reward':
                if triggered_rewards is not None and effect and effect.get('trigger_once', False):
                    reward_type = action.get('reward')
                    if reward_type in triggered_rewards:
                        continue
                    triggered_rewards.add(reward_type)
                self._apply_reward(unit, action, hp_list, unit_idx, time, log, event_callback, side, attacking_team, attacking_hp)

    def _apply_stat_buff(
        self,
        unit: 'CombatUnit',
        effect: Dict[str, Any],
        hp_list: List[int],
        unit_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ):
        """Apply stat buff from an effect."""
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
                unit.attack += add
                log.append(f"{unit.name} gains +{add} Atak (on death)")
                if event_callback:
                    event_callback('stat_buff', {
                        'unit_id': unit.id,
                        'unit_name': unit.name,
                        'stat': 'attack',
                        'amount': add,
                        'side': side,
                        'timestamp': time
                    })
            elif st == 'defense':
                if is_pct:
                    add = int(unit.defense * (val / 100.0))
                else:
                    add = int(val)
                mult = 1.0
                for beff in getattr(unit, 'effects', []):
                    if beff.get('type') == 'buff_amplifier':
                        mult = max(mult, float(beff.get('multiplier', 1)))
                add = int(add * mult)
                unit.defense += add
                log.append(f"{unit.name} gains +{add} Obrona (on death)")
                if event_callback:
                    event_callback('stat_buff', {
                        'unit_id': unit.id,
                        'unit_name': unit.name,
                        'stat': 'defense',
                        'amount': add,
                        'side': side,
                        'timestamp': time
                    })
            if st == 'hp':
                if is_pct:
                    add = int(unit.max_hp * (val / 100.0))
                else:
                    add = int(val)
                mult = 1.0
                for beff in getattr(unit, 'effects', []):
                    if beff.get('type') == 'buff_amplifier':
                        mult = max(mult, float(beff.get('multiplier', 1)))
                add = int(add * mult)
                hp_list[unit_idx] = min(unit.max_hp, hp_list[unit_idx] + add)
                log.append(f"{unit.name} heals +{add} HP (on death)")
                if event_callback:
                    event_callback('heal', {
                        'unit_id': unit.id,
                        'unit_name': unit.name,
                        'amount': add,
                        'side': side,
                        'unit_hp': hp_list[unit_idx],
                        'unit_max_hp': unit.max_hp,
                        'timestamp': time
                    })
            elif st == 'attack_speed':
                if is_pct:
                    add = unit.attack_speed * (val / 100.0)
                else:
                    add = float(val)
                mult = 1.0
                for beff in getattr(unit, 'effects', []):
                    if beff.get('type') == 'buff_amplifier':
                        mult = max(mult, float(beff.get('multiplier', 1)))
                add = add * mult
                unit.attack_speed += add
                log.append(f"{unit.name} gains +{add:.2f} Attack Speed (on death)")
                if event_callback:
                    event_callback('stat_buff', {
                        'unit_id': unit.id,
                        'unit_name': unit.name,
                        'stat': 'attack_speed',
                        'amount': add,
                        'side': side,
                        'timestamp': time
                    })
            elif st == 'mana_regen':
                if is_pct:
                    add = int(unit.mana_regen * (val / 100.0))
                else:
                    add = int(val)
                mult = 1.0
                for beff in getattr(unit, 'effects', []):
                    if beff.get('type') == 'buff_amplifier':
                        mult = max(mult, float(beff.get('multiplier', 1)))
                add = int(add * mult)
                unit.mana_regen += add
                log.append(f"{unit.name} gains +{add} Mana Regen (on death)")
                if event_callback:
                    event_callback('stat_buff', {
                        'unit_id': unit.id,
                        'unit_name': unit.name,
                        'stat': 'mana_regen',
                        'amount': add,
                        'side': side,
                        'timestamp': time
                    })
            elif st == 'lifesteal':
                if is_pct:
                    add = val / 100.0
                else:
                    add = float(val)
                mult = 1.0
                for beff in getattr(unit, 'effects', []):
                    if beff.get('type') == 'buff_amplifier':
                        mult = max(mult, float(beff.get('multiplier', 1)))
                add = add * mult
                unit.lifesteal += add
                log.append(f"{unit.name} gains +{add:.1%} Lifesteal (on death)")
                if event_callback:
                    event_callback('stat_buff', {
                        'unit_id': unit.id,
                        'unit_name': unit.name,
                        'stat': 'lifesteal',
                        'amount': add,
                        'side': side,
                        'timestamp': time
                    })
            elif st == 'damage_reduction':
                if is_pct:
                    add = val / 100.0
                else:
                    add = float(val)
                mult = 1.0
                for beff in getattr(unit, 'effects', []):
                    if beff.get('type') == 'buff_amplifier':
                        mult = max(mult, float(beff.get('multiplier', 1)))
                add = add * mult
                unit.damage_reduction += add
                log.append(f"{unit.name} gains +{add:.1%} Damage Reduction (on death)")
                if event_callback:
                    event_callback('stat_buff', {
                        'unit_id': unit.id,
                        'unit_name': unit.name,
                        'stat': 'damage_reduction',
                        'amount': add,
                        'side': side,
                        'timestamp': time
                    })
            elif st == 'hp_regen_per_sec':
                if is_pct:
                    add = unit.max_hp * (val / 100.0)
                else:
                    add = float(val)
                mult = 1.0
                for beff in getattr(unit, 'effects', []):
                    if beff.get('type') == 'buff_amplifier':
                        mult = max(mult, float(beff.get('multiplier', 1)))
                add = add * mult
                unit.hp_regen_per_sec += add
                log.append(f"{unit.name} gains +{add:.2f} HP Regen/sec (on death)")
                if event_callback:
                    event_callback('regen_gain', {
                        'unit_id': unit.id,
                        'unit_name': unit.name,
                        'amount_per_sec': add,
                        'side': side,
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