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
                    if stat == 'defense':
                        if is_pct:
                            add = int(u.defense * (val / 100.0) * mult)
                        else:
                            add = int(val * mult)
                        u.defense += add
                        log.append(f"{u.name} +{add} Defense (per second)")
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
                    if stat == 'defense':
                        if is_pct:
                            add = int(u.defense * (val / 100.0) * mult_b)
                        else:
                            add = int(val * mult_b)
                        u.defense += add
                        log.append(f"{u.name} +{add} Defense (per second)")
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