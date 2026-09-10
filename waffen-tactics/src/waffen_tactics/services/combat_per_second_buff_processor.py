"""
Combat per-second buff processor - handles buffs applied every second.
"""
from typing import List, Dict, Any, Callable, Optional

from .event_canonicalizer import emit_stat_buff, emit_hp_regen, emit_mana_change


class CombatPerSecondBuffProcessor:
    """Handles per-second buffs for units."""

    def _get_buff_amplifier(self, unit: 'CombatUnit') -> float:
        """Return the strongest valid buff amplifier on a unit."""
        multiplier = 1.0
        for effect in getattr(unit, 'effects', []):
            if effect.get('type') != 'buff_amplifier':
                continue
            try:
                multiplier = max(multiplier, float(effect.get('multiplier', 1)))
            except Exception:
                pass
        return multiplier

    def _apply_hp_regen(
        self,
        unit: 'CombatUnit',
        hp_mirror: List[int],
        unit_index: int,
        amount: int,
        side: str,
        time: float,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    ) -> None:
        """Apply HP regeneration with a canonical-first mirror commit.

        The simulator's HP list is authoritative for combat processing, while
        the unit HP property is authoritative for emitted event payloads. A
        canonical setter failure must leave both states unchanged, so the
        mirror is committed only after the canonical mutation succeeds.

        Direct processor callers historically receive mirror-only behavior when
        no callback is supplied; keep that compatibility path intact.
        """
        old_hp = int(hp_mirror[unit_index])
        if event_callback is None:
            hp_mirror[unit_index] = min(int(unit.max_hp), old_hp + int(amount))
            return

        from .event_canonicalizer import _set_and_verify_canonical_hp

        try:
            payload = emit_hp_regen(
                event_callback,
                unit,
                amount,
                side=side,
                timestamp=time,
                current_hp=old_hp,
            )
        except Exception:
            # A callback may fail after the canonical setter has accepted the
            # value. Restore the unit so the mirror and unit cannot diverge on
            # a failed operation. A setter rejection normally leaves the old
            # value untouched, so no rollback write is needed in that case.
            try:
                actual_hp = int(getattr(unit, 'hp'))
            except Exception:
                actual_hp = old_hp
            if actual_hp != old_hp:
                _set_and_verify_canonical_hp(unit, old_hp)
                if int(getattr(unit, 'hp')) != old_hp:
                    raise RuntimeError(
                        f"Failed to roll back HP regen for unit={getattr(unit, 'id', None)}"
                    )
            raise

        if payload is not None:
            hp_mirror[unit_index] = int(payload['post_hp'])
        else:
            # Canonical mutation can complete without an event if the target
            # becomes dead during emission; mirror the resulting unit state.
            hp_mirror[unit_index] = int(getattr(unit, 'hp'))

    def _process_per_second_buffs_for_team(
        self,
        team: List['CombatUnit'],
        hp_mirror: List[int],
        side: str,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    ) -> None:
        """Process one team's per-second buffs.

        Keeping both teams on this shared path prevents state-ordering and
        event-contract drift between Team A and Team B.
        """
        for unit_index, unit in enumerate(team):
            # Do not apply any timed mutation (including mana regeneration) to
            # a defeated unit. The HP arrays are the simulator's source of
            # truth, while _dead covers already-emitted death events.
            if hp_mirror[unit_index] <= 0 or getattr(unit, '_dead', False):
                continue

            for effect in getattr(unit, 'effects', []):
                if effect.get('type') == 'per_second_buff':
                    stat = effect.get('stat')
                    value = effect.get('value', 0)
                    is_percentage = effect.get('is_percentage', False)
                    multiplier = self._get_buff_amplifier(unit)

                    if stat == 'attack':
                        if is_percentage:
                            amount = int(unit.attack * (value / 100.0) * multiplier)
                        else:
                            amount = int(value * multiplier)
                        log.append(f"{unit.name} +{amount} Atak (per second)")
                        emit_stat_buff(
                            event_callback, unit, 'attack', amount,
                            value_type='flat', duration=None, permanent=False,
                            source=None, side=side, timestamp=time,
                            cause='per_second_buff',
                        )

                    if stat == 'defense':
                        if is_percentage:
                            amount = int(unit.defense * (value / 100.0) * multiplier)
                        else:
                            amount = int(value * multiplier)
                        log.append(f"{unit.name} +{amount} Defense (per second)")
                        emit_stat_buff(
                            event_callback, unit, 'defense', amount,
                            value_type='flat', duration=None, permanent=False,
                            source=None, side=side, timestamp=time,
                            cause='per_second_buff',
                        )

                    if stat == 'attack_speed':
                        if is_percentage:
                            amount = unit.attack_speed * (value / 100.0) * multiplier
                        else:
                            amount = float(value)
                        # Preserve the existing attack-speed amplifier
                        # application contract, including its second pass.
                        attack_speed_multiplier = 1.0
                        for amplifier in getattr(unit, 'effects', []):
                            if amplifier.get('type') == 'buff_amplifier':
                                try:
                                    attack_speed_multiplier = max(
                                        attack_speed_multiplier,
                                        float(amplifier.get('multiplier', 1)),
                                    )
                                except Exception:
                                    pass
                        amount *= attack_speed_multiplier
                        log.append(
                            f"{unit.name} gains +{amount:.2f} Attack Speed (per second)"
                        )
                        emit_stat_buff(
                            event_callback, unit, 'attack_speed', amount,
                            value_type='flat', duration=None, permanent=False,
                            source=None, side=side, timestamp=time,
                            cause='per_second_buff',
                        )

                    if stat == 'hp':
                        if is_percentage:
                            amount = int(unit.max_hp * (value / 100.0) * multiplier)
                        else:
                            amount = int(value * multiplier)
                        # Do not apply HP-per-second effects to dead units.
                        try:
                            if int(hp_mirror[unit_index]) <= 0:
                                continue
                        except Exception:
                            pass
                        self._apply_hp_regen(
                            unit,
                            hp_mirror,
                            unit_index,
                            amount,
                            side,
                            time,
                            event_callback,
                        )
                        log.append(f"{unit.name} {amount:+d} HP (per second)")
                        # Per-second buffs are direct stat modifications, not effects.

                elif effect.get('type') == 'mana_regen':
                    regen_amount = effect.get('value', 0)
                    if regen_amount > 0:
                        log.append(f"{unit.name} regenerates +{regen_amount} Mana")
                        if event_callback:
                            combat_state = getattr(self, '_combat_state', None)
                            if combat_state is not None:
                                emit_mana_change(
                                    event_callback,
                                    unit,
                                    regen_amount,
                                    side=side,
                                    timestamp=time,
                                    mana_arrays=combat_state.mana_arrays,
                                    unit_index=unit_index,
                                    unit_side=side,
                                )
                            else:
                                emit_mana_change(
                                    event_callback,
                                    unit,
                                    regen_amount,
                                    side=side,
                                    timestamp=time,
                                )

    def _process_per_second_buffs(
        self,
        team_a: List['CombatUnit'],
        team_b: List['CombatUnit'],
        a_hp: List[int],
        b_hp: List[int],
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    ):
        """Apply per-second buffs for both teams."""
        self._process_per_second_buffs_for_team(
            team_a, a_hp, 'team_a', time, log, event_callback
        )
        self._process_per_second_buffs_for_team(
            team_b, b_hp, 'team_b', time, log, event_callback
        )
