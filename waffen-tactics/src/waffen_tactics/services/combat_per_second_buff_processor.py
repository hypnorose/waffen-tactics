"""
Combat per-second buff processor - handles buffs applied every second
"""
from typing import List, Dict, Any, Callable, Optional


class CombatPerSecondBuffProcessor:
    """Handles per-second buffs for units"""

    def _process_per_second_buffs(
        self,
        team_a: List['CombatUnit'],
        team_b: List['CombatUnit'],
        a_hp: List[int],
        b_hp: List[int],
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]]
    ):
        """Apply per-second buffs for both teams."""
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
                        if event_callback and add != 0:
                            event_callback('stat_buff', {
                                'unit_id': u.id,
                                'unit_name': u.name,
                                'stat': 'attack',
                                'amount': add,
                                'side': 'team_a',
                                'timestamp': time,
                                'cause': 'effect'
                            })
                    if stat == 'defense':
                        if is_pct:
                            add = int(u.defense * (val / 100.0) * mult)
                        else:
                            add = int(val * mult)
                        u.defense += add
                        log.append(f"{u.name} +{add} Defense (per second)")
                        if event_callback and add != 0:
                            event_callback('stat_buff', {
                                'unit_id': u.id,
                                'unit_name': u.name,
                                'stat': 'defense',
                                'amount': add,
                                'side': 'team_a',
                                'timestamp': time,
                                'cause': 'effect'
                            })
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
                elif eff.get('type') == 'mana_regen':
                    # Handle mana regeneration
                    regen_amount = eff.get('value', 0)
                    if regen_amount > 0:
                        old_mana = u.mana
                        u.mana = min(u.max_mana, u.mana + regen_amount)
                        gained = u.mana - old_mana
                        if gained > 0:
                            log.append(f"{u.name} regenerates +{gained} Mana")
                            if event_callback:
                                event_callback('mana_regen', {
                                    'unit_id': u.id,
                                    'unit_name': u.name,
                                    'amount': gained,
                                    'current_mana': u.mana,
                                    'max_mana': u.max_mana,
                                    'side': 'team_a',
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
                        if event_callback and add != 0:
                            event_callback('stat_buff', {
                                'unit_id': u.id,
                                'unit_name': u.name,
                                'stat': 'attack',
                                'amount': add,
                                'side': 'team_b',
                                'timestamp': time
                            })
                    if stat == 'defense':
                        if is_pct:
                            add = int(u.defense * (val / 100.0) * mult_b)
                        else:
                            add = int(val * mult_b)
                        u.defense += add
                        log.append(f"{u.name} +{add} Defense (per second)")
                        if event_callback and add != 0:
                            event_callback('stat_buff', {
                                'unit_id': u.id,
                                'unit_name': u.name,
                                'stat': 'defense',
                                'amount': add,
                                'side': 'team_b',
                                'timestamp': time
                            })
                    if stat == 'attack_speed':
                        if is_pct:
                            add = u.attack_speed * (val / 100.0) * mult_b
                        else:
                            add = float(val)
                        # apply any buff amplifier present
                        amp = 1.0
                        for beff in getattr(u, 'effects', []):
                            if beff.get('type') == 'buff_amplifier':
                                try:
                                    amp = max(amp, float(beff.get('multiplier', 1)))
                                except Exception:
                                    pass
                        add = add * amp
                        u.attack_speed += add
                        log.append(f"{u.name} gains +{add:.2f} Attack Speed (per second)")
                        if event_callback and add != 0:
                            event_callback('stat_buff', {
                                'unit_id': u.id,
                                'unit_name': u.name,
                                'stat': 'attack_speed',
                                'amount': add,
                                'side': 'team_b',
                                'timestamp': time,
                                'cause': 'effect'
                            })
                    if stat == 'hp':
                        if is_pct:
                            add = int(u.max_hp * (val / 100.0) * mult_b)
                        else:
                            add = int(val * mult_b)
                        if event_callback and add != 0:
                            event_callback('stat_buff', {
                                'unit_id': u.id,
                                'unit_name': u.name,
                                'stat': 'hp',
                                'amount': add,
                                'side': 'team_b',
                                'timestamp': time,
                                'cause': 'effect'
                            })
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
                elif eff.get('type') == 'mana_regen':
                    # Handle mana regeneration
                    regen_amount = eff.get('value', 0)
                    if regen_amount > 0:
                        old_mana = u.mana
                        u.mana = min(u.max_mana, u.mana + regen_amount)
                        gained = u.mana - old_mana
                        if gained > 0:
                            log.append(f"{u.name} regenerates +{gained} Mana")
                            if event_callback:
                                event_callback('mana_regen', {
                                    'unit_id': u.id,
                                    'unit_name': u.name,
                                    'amount': gained,
                                    'current_mana': u.mana,
                                    'max_mana': u.max_mana,
                                    'side': 'team_b',
                                    'timestamp': time
                                })