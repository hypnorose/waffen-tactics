"""
Combat effect processor - handles trait effects, buffs, and death triggers
"""
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

        # Killer-specific effects for 'hp_regen_on_kill'
        for eff in getattr(killer, 'effects', []):
            if eff.get('type') == 'hp_regen_on_kill':
                is_pct = eff.get('is_percentage', False)
                val = float(eff.get('value', 0))
                duration = float(eff.get('duration', 5.0))
                if duration <= 0:
                    duration = 5.0
                if is_pct:
                    total_amount = killer.max_hp * (val / 100.0)
                else:
                    total_amount = float(val)
                add_per_sec = total_amount / duration
                if add_per_sec > 0:
                    killer.hp_regen_per_sec += add_per_sec
                    log.append(f"[{time:.2f}s] {killer.name} gains +{total_amount:.2f} HP over {duration}s (+{add_per_sec:.2f} HP/s) (on kill)")
                    if event_callback:
                        event_callback('regen_gain', {
                            'unit_id': killer.id,
                            'timestamp': time,
                            'unit_name': killer.name,
                            'amount_per_sec': add_per_sec,
                            'total_amount': total_amount,
                            'duration': duration,
                            'side': side
                        })

        # Trigger on_enemy_death effects for attacking team
        for unit in attacking_team:
            for eff in getattr(unit, 'effects', []):
                if eff.get('type') == 'on_enemy_death':
                    self._apply_stat_buff(unit, eff, attacking_hp, attacking_team.index(unit), time, log, event_callback, side)

        # Trigger on_ally_death effects for surviving allies on defending team
        for i, unit in enumerate(defending_team):
            if defending_hp[i] <= 0:
                continue
            for eff in getattr(unit, 'effects', []):
                if eff.get('type') == 'on_ally_death':
                    # Handle reward effects (e.g. Denciak: gold on ally death)
                    if eff.get('reward') == 'gold':
                        amount = int(eff.get('value', 0))
                        log.append(f"{unit.name} triggers reward: +{amount} gold (ally died)")
                        if event_callback:
                            event_callback('gold_reward', {
                                'amount': amount,
                                'unit_id': getattr(unit, 'id', None),
                                'unit_name': getattr(unit, 'name', None),
                                'side': defending_side,
                                'timestamp': time
                            })
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
                        'unit_max_hp': unit.max_hp
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
                                'unit_max_hp': team[target_idx].max_hp
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
                if eff.get('type') == 'per_round_buff':
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
                        log.append(f"{u.name} +{add} Atak (per round)")
                    if stat == 'hp':
                        if is_pct:
                            add = int(u.max_hp * (val / 100.0) * mult)
                        else:
                            add = int(val * mult)
                        a_hp[idx_u] = min(u.max_hp, a_hp[idx_u] + add)
                        log.append(f"{u.name} +{add} HP (per round)")
                        if event_callback and add > 0:
                            event_callback('heal', {
                                'unit_id': u.id,
                                'unit_name': u.name,
                                'amount': add,
                                'side': 'team_a',
                                'unit_hp': a_hp[idx_u],
                                'unit_max_hp': u.max_hp
                            })

        # Team B buffs
        for idx_u, u in enumerate(team_b):
            for eff in getattr(u, 'effects', []):
                if eff.get('type') == 'per_round_buff':
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
                        log.append(f"{u.name} +{add} Atak (per round)")
                    if stat == 'hp':
                        if is_pct:
                            add = int(u.max_hp * (val / 100.0) * mult_b)
                        else:
                            add = int(val * mult_b)
                        b_hp[idx_u] = min(u.max_hp, b_hp[idx_u] + add)
                        log.append(f"{u.name} +{add} HP (per round)")
                        if event_callback and add > 0:
                            event_callback('heal', {
                                'unit_id': u.id,
                                'unit_name': u.name,
                                'amount': add,
                                'side': 'team_b',
                                'unit_hp': b_hp[idx_u],
                                'unit_max_hp': u.max_hp
                            })