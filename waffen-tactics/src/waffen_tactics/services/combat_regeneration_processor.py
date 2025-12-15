"""
Combat regeneration processor - handles HP regeneration over time
"""
from typing import List, Dict, Any, Callable, Optional


class CombatRegenerationProcessor:
    """Handles HP regeneration over time"""

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
        """Apply HP regeneration for both teams."""
        # Team A regen
        for idx_u, u in enumerate(team_a):
            if a_hp[idx_u] > 0 and getattr(u, 'hp_regen_per_sec', 0.0) > 0:
                heal = u.hp_regen_per_sec * dt
                # accumulate fractional healing
                u._hp_regen_accumulator += heal
                int_heal = int(u._hp_regen_accumulator)
                if int_heal > 0:
                    u._hp_regen_accumulator -= int_heal
                    a_hp[idx_u] = min(u.max_hp, a_hp[idx_u] + int_heal)
                    log.append(f"{u.name} regenerates +{int_heal} HP (regen over time)")
                    if event_callback:
                        event_callback('heal', {
                            'unit_id': u.id,
                            'unit_name': u.name,
                            'amount': int_heal,
                            'side': 'team_a',
                            'unit_hp': a_hp[idx_u],
                            'unit_max_hp': u.max_hp,
                            'timestamp': time
                        })

        # Team B regen
        for idx_u, u in enumerate(team_b):
            if b_hp[idx_u] > 0 and getattr(u, 'hp_regen_per_sec', 0.0) > 0:
                heal_b = u.hp_regen_per_sec * dt
                u._hp_regen_accumulator += heal_b
                int_heal_b = int(u._hp_regen_accumulator)
                if int_heal_b > 0:
                    u._hp_regen_accumulator -= int_heal_b
                    b_hp[idx_u] = min(u.max_hp, b_hp[idx_u] + int_heal_b)
                    log.append(f"{u.name} regenerates +{int_heal_b} HP (regen over time)")
                    if event_callback:
                        event_callback('heal', {
                            'unit_id': u.id,
                            'unit_name': u.name,
                            'amount': int_heal_b,
                            'side': 'team_b',
                            'unit_hp': b_hp[idx_u],
                            'unit_max_hp': u.max_hp,
                            'timestamp': time
                        })