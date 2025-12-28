"""
Combat per-second buff processor - handles buffs applied every second
"""
from typing import List, Dict, Any, Callable, Optional
from .event_canonicalizer import emit_stat_buff, emit_hp_regen, emit_mana_change


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
                        log.append(f"{u.name} +{add} Atak (per second)")
                        emit_stat_buff(event_callback, u, 'attack', add, value_type='flat', duration=None, permanent=False, source=None, side='team_a', timestamp=time, cause='per_second_buff')
                    if stat == 'defense':
                        if is_pct:
                            add = int(u.defense * (val / 100.0) * mult)
                        else:
                            add = int(val * mult)
                        log.append(f"{u.name} +{add} Defense (per second)")
                        emit_stat_buff(event_callback, u, 'defense', add, value_type='flat', duration=None, permanent=False, source=None, side='team_a', timestamp=time, cause='per_second_buff')
                    if stat == 'attack_speed':
                        if is_pct:
                            add = u.attack_speed * (val / 100.0) * mult
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
                        log.append(f"{u.name} gains +{add:.2f} Attack Speed (per second)")
                        emit_stat_buff(event_callback, u, 'attack_speed', add, value_type='flat', duration=None, permanent=False, source=None, side='team_a', timestamp=time, cause='per_second_buff')
                    if stat == 'hp':
                        if is_pct:
                            add = int(u.max_hp * (val / 100.0) * mult)
                        else:
                            add = int(val * mult)
                        # Do not apply HP-per-second effects to dead units
                        try:
                            if int(a_hp[idx_u]) <= 0:
                                continue
                        except Exception:
                            pass
                        old_hp = int(a_hp[idx_u])
                        a_hp[idx_u] = min(u.max_hp, a_hp[idx_u] + add)
                        new_hp = int(a_hp[idx_u])
                        log.append(f"{u.name} {add:+d} HP (per second)")
                        # print(f"[HP DEBUG] ts={time:.9f} side=team_a target={u.id}:{u.name} old_hp={old_hp} -> new_hp={new_hp} cause=per_second_buff add={add}")
                        if event_callback:
                            emit_hp_regen(event_callback, u, add, side='team_a', timestamp=time, current_hp=old_hp)
                        # Per-second buffs are direct stat modifications, not effects
                elif eff.get('type') == 'mana_regen':
                    # Handle mana regeneration
                    regen_amount = eff.get('value', 0)
                    if regen_amount > 0:
                        log.append(f"{u.name} regenerates +{regen_amount} Mana")
                        if event_callback:
                            combat_state = getattr(self, '_combat_state', None)
                            if combat_state is not None:
                                emit_mana_change(event_callback, u, regen_amount, side='team_a', timestamp=time, mana_arrays=combat_state.mana_arrays, unit_index=idx_u, unit_side='team_a')
                            else:
                                emit_mana_change(event_callback, u, regen_amount, side='team_a', timestamp=time)

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
                        log.append(f"{u.name} +{add} Atak (per second)")
                        emit_stat_buff(event_callback, u, 'attack', add, value_type='flat', duration=None, permanent=False, source=None, side='team_b', timestamp=time, cause='per_second_buff')
                    if stat == 'defense':
                        if is_pct:
                            add = int(u.defense * (val / 100.0) * mult_b)
                        else:
                            add = int(val * mult_b)
                        log.append(f"{u.name} +{add} Defense (per second)")
                        emit_stat_buff(event_callback, u, 'defense', add, value_type='flat', duration=None, permanent=False, source=None, side='team_b', timestamp=time, cause='per_second_buff')
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
                        log.append(f"{u.name} gains +{add:.2f} Attack Speed (per second)")
                        emit_stat_buff(event_callback, u, 'attack_speed', add, value_type='flat', duration=None, permanent=False, source=None, side='team_b', timestamp=time, cause='per_second_buff')
                    if stat == 'hp':
                        if is_pct:
                            add = int(u.max_hp * (val / 100.0) * mult_b)
                        else:
                            add = int(val * mult_b)
                        # Do not apply HP-per-second effects to dead units
                        try:
                            if int(b_hp[idx_u]) <= 0:
                                continue
                        except Exception:
                            pass
                        old_hp_b = int(b_hp[idx_u])
                        b_hp[idx_u] = min(u.max_hp, b_hp[idx_u] + add)
                        new_hp_b = int(b_hp[idx_u])
                        log.append(f"{u.name} {add:+d} HP (per second)")
                        # print(f"[HP DEBUG] ts={time:.9f} side=team_b target={u.id}:{u.name} old_hp={old_hp_b} -> new_hp={new_hp_b} cause=per_second_buff add={add}")
                        if event_callback:
                            emit_hp_regen(event_callback, u, add, side='team_b', timestamp=time, current_hp=old_hp_b)
                        # Per-second buffs are direct stat modifications, not effects
                elif eff.get('type') == 'mana_regen':
                    # Handle mana regeneration
                    regen_amount = eff.get('value', 0)
                    if regen_amount > 0:
                        log.append(f"{u.name} regenerates +{regen_amount} Mana")
                        if event_callback:
                            combat_state = getattr(self, '_combat_state', None)
                            if combat_state is not None:
                                emit_mana_change(event_callback, u, regen_amount, side='team_b', timestamp=time, mana_arrays=combat_state.mana_arrays, unit_index=idx_u, unit_side='team_b')
                            else:
                                emit_mana_change(event_callback, u, regen_amount, side='team_b', timestamp=time)