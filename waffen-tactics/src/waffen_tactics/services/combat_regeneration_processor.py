"""
Combat regeneration processor - handles HP and mana regeneration over time
"""
from typing import List, Dict, Any, Callable, Optional
from .event_canonicalizer import emit_heal, emit_mana_change


class CombatRegenerationProcessor:
    """Handles HP and mana regeneration over time"""

    def _process_regeneration(
        self,
        team_a: List['CombatUnit'],
        team_b: List['CombatUnit'],
        a_hp: List[int],
        b_hp: List[int],
        time: float,
        log: List[str],
        dt: float,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]]
    ):
        """Apply HP and mana regeneration for both teams."""
        # Team A regen
        for idx_u, u in enumerate(team_a):
            # HP regeneration
            if a_hp[idx_u] > 0 and getattr(u, 'hp_regen_per_sec', 0.0) > 0:
                heal = u.hp_regen_per_sec * dt
                # accumulate fractional healing
                u._hp_regen_accumulator += heal
                int_heal = int(round(u._hp_regen_accumulator))
                if int_heal > 0:
                    u._hp_regen_accumulator -= int_heal
                    old_hp = int(a_hp[idx_u])
                    a_hp[idx_u] = min(u.max_hp, a_hp[idx_u] + int_heal)
                    new_hp = int(a_hp[idx_u])
                    log.append(f"{u.name} regenerates +{int_heal} HP (regen over time)")
                    # print(f"[HP DEBUG] ts={time:.9f} side=team_a target={u.id}:{u.name} old_hp={old_hp} -> new_hp={new_hp} cause=regen int_heal={int_heal}")
                    if event_callback:
                        emit_heal(event_callback, u, int_heal, source=None, side='team_a', timestamp=time)

            # Mana regeneration
            if getattr(u, 'mana_regen', 0) > 0:
                mana_gain = u.mana_regen * dt
                # accumulate fractional mana gain
                if not hasattr(u, '_mana_regen_accumulator'):
                    u._mana_regen_accumulator = 0.0
                u._mana_regen_accumulator += mana_gain
                int_mana = int(round(u._mana_regen_accumulator))
                if int_mana > 0:
                    u._mana_regen_accumulator -= int_mana
                    old_mana = u.mana
                    u.mana = min(u.max_mana, u.mana + int_mana)
                    gained = u.mana - old_mana
                    if gained > 0:
                        log.append(f"{u.name} regenerates +{gained} Mana")
                        if event_callback:
                            emit_mana_change(event_callback, u, gained, side='team_a', timestamp=time)

        # Team B regen
        for idx_u, u in enumerate(team_b):
            # HP regeneration
            if b_hp[idx_u] > 0 and getattr(u, 'hp_regen_per_sec', 0.0) > 0:
                heal_b = u.hp_regen_per_sec * dt
                u._hp_regen_accumulator += heal_b
                int_heal_b = int(round(u._hp_regen_accumulator))
                if int_heal_b > 0:
                    u._hp_regen_accumulator -= int_heal_b
                    old_hp_b = int(b_hp[idx_u])
                    b_hp[idx_u] = min(u.max_hp, b_hp[idx_u] + int_heal_b)
                    new_hp_b = int(b_hp[idx_u])
                    log.append(f"{u.name} regenerates +{int_heal_b} HP (regen over time)")
                    # print(f"[HP DEBUG] ts={time:.9f} side=team_b target={u.id}:{u.name} old_hp={old_hp_b} -> new_hp={new_hp_b} cause=regen int_heal={int_heal_b}")
                    if event_callback:
                        emit_heal(event_callback, u, int_heal_b, source=None, side='team_b', timestamp=time)

            # Mana regeneration
            if getattr(u, 'mana_regen', 0) > 0:
                mana_gain_b = u.mana_regen * dt
                if not hasattr(u, '_mana_regen_accumulator'):
                    u._mana_regen_accumulator = 0.0
                u._mana_regen_accumulator += mana_gain_b
                int_mana_b = int(round(u._mana_regen_accumulator))
                if int_mana_b > 0:
                    u._mana_regen_accumulator -= int_mana_b
                    old_mana_b = u.mana
                    u.mana = min(u.max_mana, u.mana + int_mana_b)
                    gained_b = u.mana - old_mana_b
                    if gained_b > 0:
                        log.append(f"{u.name} regenerates +{gained_b} Mana")
                        if event_callback:
                            emit_mana_change(event_callback, u, gained_b, side='team_b', timestamp=time)