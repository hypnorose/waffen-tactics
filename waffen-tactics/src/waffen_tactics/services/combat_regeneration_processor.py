"""
Combat regeneration processor - handles HP and mana regeneration over time.
"""
from typing import List, Dict, Any, Callable, Optional
import math

from .event_canonicalizer import emit_heal, emit_mana_change


class CombatRegenerationProcessor:
    """Handles HP and mana regeneration over time."""

    def _apply_hp_regeneration_tick(
        self,
        unit: 'CombatUnit',
        hp_mirror: List[int],
        unit_index: int,
        side: str,
        time: float,
        log: List[str],
        dt: float,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    ) -> None:
        """Apply one integral HP-regeneration tick atomically.

        The fractional accumulator is only consumed after canonical HP
        mutation and verification succeed. This keeps retry behavior correct
        when a recipient rejects the write or event delivery fails.
        """
        set2_regen = sum(
            float(effect.get('amount_per_sec', 0.0))
            for effect in getattr(unit, 'effects', [])
            if effect.get('type') == 'set2_regen_over_time'
            and time < float(effect.get('expires_at', time))
        )
        total_hp_regen = float(getattr(unit, 'hp_regen_per_sec', 0.0)) + set2_regen
        if total_hp_regen <= 0:
            return

        if not hasattr(unit, '_hp_regen_accumulator'):
            if hasattr(unit, '_state') and hasattr(unit._state, 'hp_regen_accumulator'):
                unit._hp_regen_accumulator = float(unit._state.hp_regen_accumulator)
            else:
                unit._hp_regen_accumulator = 0.0

        previous_accumulator = float(unit._hp_regen_accumulator)
        pending_regeneration = previous_accumulator + (
            total_hp_regen * dt
        )
        integral_heal = int(pending_regeneration)
        if integral_heal <= 0:
            unit._hp_regen_accumulator = pending_regeneration
            return

        old_hp = int(hp_mirror[unit_index])
        from .event_canonicalizer import _set_and_verify_canonical_hp

        try:
            payload = emit_heal(
                event_callback,
                unit,
                integral_heal,
                source=None,
                side=side,
                timestamp=time,
                current_hp=old_hp,
            )
        except Exception:
            # `emit_heal` mutates through the canonical boundary. If delivery
            # fails after that mutation, restore the unit; the mirror and
            # accumulator have not been committed yet.
            try:
                actual_hp = int(getattr(unit, 'hp'))
            except Exception:
                actual_hp = old_hp
            if actual_hp != old_hp:
                _set_and_verify_canonical_hp(unit, old_hp)
                if int(getattr(unit, 'hp')) != old_hp:
                    raise RuntimeError(
                        f"Failed to roll back HP regeneration for unit={getattr(unit, 'id', None)}"
                    )
            raise

        if payload is not None:
            hp_mirror[unit_index] = int(payload['post_hp'])
            log.append(
                f"{unit.name} regenerates +{integral_heal} HP (regen over time)"
            )
        else:
            # The canonical mutation may complete while event publication is
            # suppressed for a target that became dead during the operation.
            hp_mirror[unit_index] = int(getattr(unit, 'hp'))

        # Commit fractional consumption only after canonical HP and mirror
        # state have completed successfully.
        unit._hp_regen_accumulator = pending_regeneration - integral_heal

    def _process_mana_regeneration_for_unit(
        self,
        unit: 'CombatUnit',
        unit_index: int,
        side: str,
        time: float,
        log: List[str],
        dt: float,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    ) -> None:
        """Apply one unit's effect/base mana regeneration."""
        base_mana_regen = getattr(unit.stats, 'mana_regen', 0)
        effect_bonus = sum(
            float(effect.get('value', 0))
            for effect in getattr(unit, 'effects', [])
            if effect.get('type') == 'mana_regen'
        )
        multiplier = 1.0
        multiplier_expires_at = getattr(unit, '_set2_mana_regen_expires_at', None)
        if multiplier_expires_at is None or time <= float(multiplier_expires_at):
            multiplier = float(getattr(unit, '_set2_mana_regen_multiplier', 1.0) or 1.0)
        total_mana_regen = (base_mana_regen + effect_bonus) * multiplier
        if total_mana_regen <= 0:
            return

        mana_gain = total_mana_regen * dt
        if not hasattr(unit, '_mana_regen_accumulator'):
            unit._mana_regen_accumulator = 0.0
        unit._mana_regen_accumulator += mana_gain
        integral_mana = math.floor(unit._mana_regen_accumulator + 1e-10)
        if integral_mana <= 0:
            return

        unit._mana_regen_accumulator -= integral_mana
        log.append(f"{unit.name} regenerates +{integral_mana} Mana")
        if event_callback:
            combat_state = getattr(self, '_combat_state', None)
            if combat_state is not None:
                emit_mana_change(
                    event_callback,
                    unit,
                    integral_mana,
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
                    integral_mana,
                    side=side,
                    timestamp=time,
                )

    def _process_regeneration_for_team(
        self,
        team: List['CombatUnit'],
        hp_mirror: List[int],
        side: str,
        time: float,
        log: List[str],
        dt: float,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    ) -> None:
        """Process HP and mana regeneration for one team."""
        for unit_index, unit in enumerate(team):
            # A defeated unit must not accumulate or receive any regeneration.
            # In particular, mana changes after unit_died are ignored by the
            # frontend and would otherwise desync subsequent snapshots.
            if hp_mirror[unit_index] <= 0 or getattr(unit, '_dead', False):
                continue

            self._apply_hp_regeneration_tick(
                unit,
                hp_mirror,
                unit_index,
                side,
                time,
                log,
                dt,
                event_callback,
            )
            self._process_mana_regeneration_for_unit(
                unit,
                unit_index,
                side,
                time,
                log,
                dt,
                event_callback,
            )

    def _sync_hp_mirror_for_team(
        self,
        team: List['CombatUnit'],
        hp_mirror: List[int],
        side: str,
        log: List[str],
    ) -> None:
        """Retain the existing end-of-pass HP consistency check."""
        for unit_index, unit in enumerate(team):
            if hp_mirror[unit_index] != unit.hp:
                log.append(
                    f"[COMBAT_STATE SYNC] {unit.name} {side}[{unit_index}]: "
                    f"{hp_mirror[unit_index]} -> {unit.hp} (unit.hp={unit.hp})"
                )
                hp_mirror[unit_index] = unit.hp

    def _process_regeneration(
        self,
        team_a: List['CombatUnit'],
        team_b: List['CombatUnit'],
        a_hp: List[int],
        b_hp: List[int],
        time: float,
        log: List[str],
        dt: float,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    ):
        """Apply HP and mana regeneration for both teams."""
        self._process_regeneration_for_team(
            team_a, a_hp, 'team_a', time, log, dt, event_callback
        )
        self._process_regeneration_for_team(
            team_b, b_hp, 'team_b', time, log, dt, event_callback
        )

        # Sync HP lists to unit.hp for all units to ensure consistency.
        self._sync_hp_mirror_for_team(team_a, a_hp, 'team_a', log)
        self._sync_hp_mirror_for_team(team_b, b_hp, 'team_b', log)

        # Optional debug invariant: ensure combat_state (if present) is consistent.
        try:
            combat_state = getattr(self, '_combat_state', None)
            if combat_state is not None:
                combat_state.enforce_debug_assertions()
        except Exception:
            # Propagate assertion to caller so failures are visible during testing.
            raise
