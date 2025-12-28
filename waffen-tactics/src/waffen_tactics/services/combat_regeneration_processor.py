"""
Combat regeneration processor - handles HP and mana regeneration over time
"""
from typing import List, Dict, Any, Callable, Optional
from .event_canonicalizer import emit_heal, emit_mana_change
import math


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
                # Support multiple unit shapes: prefer explicit attribute,
                # otherwise fall back to backing _state.hp_regen_accumulator.
                if not hasattr(u, '_hp_regen_accumulator'):
                    if hasattr(u, '_state') and hasattr(u._state, 'hp_regen_accumulator'):
                        u._hp_regen_accumulator = float(u._state.hp_regen_accumulator)
                    else:
                        u._hp_regen_accumulator = 0.0
                u._hp_regen_accumulator += heal
                int_heal = int(u._hp_regen_accumulator)
                if int_heal > 0:
                    u._hp_regen_accumulator -= int_heal
                    old_hp = int(a_hp[idx_u])
                    a_hp[idx_u] = min(u.max_hp, a_hp[idx_u] + int_heal)
                    new_hp = int(a_hp[idx_u])
                    log.append(f"{u.name} regenerates +{int_heal} HP (regen over time)")
                    # print(f"[HP DEBUG] ts={time:.9f} side=team_a target={u.id}:{u.name} old_hp={old_hp} -> new_hp={new_hp} cause=regen int_heal={int_heal}")
                    if event_callback:
                        emit_heal(event_callback, u, int_heal, source=None, side='team_a', timestamp=time, current_hp=old_hp)

            # Mana regeneration (include trait/effect-based bonuses)
            base_mana_regen = getattr(u.stats, 'mana_regen', 0)
            effect_bonus = sum(float(e.get('value', 0)) for e in getattr(u, 'effects', []) if e.get('type') == 'mana_regen')
            total_mana_regen = base_mana_regen + effect_bonus
            if total_mana_regen > 0:
                mana_gain = total_mana_regen * dt
                # accumulate fractional mana gain
                if not hasattr(u, '_mana_regen_accumulator'):
                    u._mana_regen_accumulator = 0.0
                u._mana_regen_accumulator += mana_gain
                int_mana = math.floor(u._mana_regen_accumulator + 1e-10)
                if int_mana > 0:
                    u._mana_regen_accumulator -= int_mana
                    log.append(f"{u.name} regenerates +{int_mana} Mana")
                    # Apply mana change via canonical emitter (it mutates state and emits)
                    combat_state = getattr(self, '_combat_state', None)
                    if combat_state is not None:
                        emit_mana_change(event_callback, u, int_mana, side='team_a', timestamp=time, mana_arrays=combat_state.mana_arrays, unit_index=idx_u, unit_side='team_a')
                    else:
                        emit_mana_change(event_callback, u, int_mana, side='team_a', timestamp=time)

        # Team B regen
        for idx_u, u in enumerate(team_b):
            # HP regeneration
            if b_hp[idx_u] > 0 and getattr(u, 'hp_regen_per_sec', 0.0) > 0:
                heal_b = u.hp_regen_per_sec * dt
                # ensure accumulator exists (see Team A logic)
                if not hasattr(u, '_hp_regen_accumulator'):
                    if hasattr(u, '_state') and hasattr(u._state, 'hp_regen_accumulator'):
                        u._hp_regen_accumulator = float(u._state.hp_regen_accumulator)
                    else:
                        u._hp_regen_accumulator = 0.0
                u._hp_regen_accumulator += heal_b
                int_heal_b = int(u._hp_regen_accumulator)
                if int_heal_b > 0:
                    u._hp_regen_accumulator -= int_heal_b
                    old_hp_b = int(b_hp[idx_u])
                    b_hp[idx_u] = min(u.max_hp, b_hp[idx_u] + int_heal_b)
                    new_hp_b = int(b_hp[idx_u])
                    log.append(f"{u.name} regenerates +{int_heal_b} HP (regen over time)")
                    # print(f"[HP DEBUG] ts={time:.9f} side=team_b target={u.id}:{u.name} old_hp={old_hp_b} -> new_hp={new_hp_b} cause=regen int_heal={int_heal_b}")
                    if event_callback:
                        emit_heal(event_callback, u, int_heal_b, source=None, side='team_b', timestamp=time, current_hp=old_hp_b)

            # Mana regeneration (include trait/effect-based bonuses)
            base_mana_regen_b = getattr(u.stats, 'mana_regen', 0)
            effect_bonus_b = sum(float(e.get('value', 0)) for e in getattr(u, 'effects', []) if e.get('type') == 'mana_regen')
            total_mana_regen_b = base_mana_regen_b + effect_bonus_b
            if total_mana_regen_b > 0:
                mana_gain_b = total_mana_regen_b * dt
                if not hasattr(u, '_mana_regen_accumulator'):
                    u._mana_regen_accumulator = 0.0
                u._mana_regen_accumulator += mana_gain_b
                int_mana_b = math.floor(u._mana_regen_accumulator + 1e-10)
                if int_mana_b > 0:
                    u._mana_regen_accumulator -= int_mana_b
                    log.append(f"{u.name} regenerates +{int_mana_b} Mana")
                    # Apply mana change via canonical emitter (it mutates state and emits)
                    combat_state = getattr(self, '_combat_state', None)
                    if combat_state is not None:
                        emit_mana_change(event_callback, u, int_mana_b, side='team_b', timestamp=time, mana_arrays=combat_state.mana_arrays, unit_index=idx_u, unit_side='team_b')
                    else:
                        emit_mana_change(event_callback, u, int_mana_b, side='team_b', timestamp=time)

        # Sync HP lists to unit.hp for all units to ensure consistency
        for idx_u, u in enumerate(team_a):
            if a_hp[idx_u] != u.hp:
                log.append(f"[COMBAT_STATE SYNC] {u.name} a_hp[{idx_u}]: {a_hp[idx_u]} -> {u.hp} (unit.hp={u.hp})")
                a_hp[idx_u] = u.hp

        for idx_u, u in enumerate(team_b):
            if b_hp[idx_u] != u.hp:
                log.append(f"[COMBAT_STATE SYNC] {u.name} b_hp[{idx_u}]: {b_hp[idx_u]} -> {u.hp} (unit.hp={u.hp})")
                b_hp[idx_u] = u.hp