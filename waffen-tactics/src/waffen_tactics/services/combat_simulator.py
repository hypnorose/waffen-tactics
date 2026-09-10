from typing import List, Dict, Any, Callable, Optional
import itertools
import heapq

from .combat_unit import CombatUnit
from .combat_attack_processor import CombatAttackProcessor
from .combat_effect_processor import CombatEffectProcessor
from .combat_regeneration_processor import CombatRegenerationProcessor
from .combat_per_second_buff_processor import CombatPerSecondBuffProcessor
from .modular_effect_processor import ModularEffectProcessor
from .passive_processor import PassiveProcessor
from ..engine.combat_state import CombatState
from ..engine.event_dispatcher import EventDispatcher


def _require_runtime_effect_id(effect_id: Any, unit: Any, effect_type: str, phase: str) -> str:
    """Fail before state mutation when a runtime effect lacks its identity."""
    if not isinstance(effect_id, str) or not effect_id.strip():
        raise RuntimeError(
            f"Cannot process {phase} for unit={getattr(unit, 'id', None)} "
            f"effect_type={effect_type!r}: missing required effect_id"
        )
    return effect_id


class _DispatcherEventSink:
    """Event sink that wraps callbacks with EventDispatcher middleware.

    Behavior:
    - If payload timestamp > simulator._current_time -> enqueue via simulator._enqueue_scheduled_event
    - Otherwise deliver immediately and assign `seq` and `event_id` similar to simulator wrapper
    """
    def __init__(self, simulator: "CombatSimulator", collector: Callable[[str, Dict[str, Any]], None]):
        self.simulator = simulator
        self.collector = collector
        self.dispatcher = EventDispatcher(
            team_a=simulator.team_a,
            team_b=simulator.team_b,
            a_hp=simulator.a_hp,
            b_hp=simulator.b_hp,
            initial_seq=simulator._event_seq,
        )
        self.wrapped_collector = self.dispatcher.wrap_callback(collector)

    def emit(self, event_type: str, payload: Dict[str, Any]):
        data = dict(payload) if isinstance(payload, dict) else payload

        ts = data.get('timestamp') if isinstance(data, dict) else None
        current = getattr(self.simulator, '_current_time', 0.0)

        if isinstance(ts, (int, float)) and ts > current:
            # Preserve the authoritative state at emission time. Without this,
            # the backend may build the event's game_state when it is delivered
            # in a later tick, making the snapshot describe a future state.
            if isinstance(data, dict) and '_event_game_state' not in data:
                data['_event_game_state'] = self.simulator._capture_runtime_state()
            self.simulator._enqueue_scheduled_event(ts, event_type, data if isinstance(data, dict) else {'payload': data})
            return

        if self.wrapped_collector:
            self.wrapped_collector(event_type, data)
            self.simulator._event_seq = self.dispatcher._event_seq

class CombatSimulator(CombatAttackProcessor, CombatEffectProcessor, CombatRegenerationProcessor, CombatPerSecondBuffProcessor):
    """Shared CombatSimulator combining processors and providing scheduling helpers.

    This class exposes the processing methods (skill casts, unit death, regen,
    per-second buffs) via multiple inheritance from processor classes and
    implements a minimal scheduler surface required by tests.
    """
    def __init__(self, dt: float = 0.1, timeout: int = 120, modular_effect_processor=None):
        # Ensure we have a modular effect processor available by default
        if modular_effect_processor is None:
            modular_effect_processor = ModularEffectProcessor()
        # Initialize processors that require construction
        CombatEffectProcessor.__init__(self, modular_effect_processor=modular_effect_processor)
        self.passive_processor = PassiveProcessor()
        # Basic simulator state
        self.dt = dt
        self.timeout = timeout
        self._scheduled = []
        self._schedule_counter = itertools.count()
        self._event_seq = 0
        self._current_time = 0.0
        # Simulator team placeholders (may be set by simulate)
        self.team_a = []
        self.team_b = []
        self.a_hp = []
        self.b_hp = []

    def _enqueue_scheduled_event(self, deliver_at: float, event_type: str, payload: Dict[str, Any]):
        cnt = next(self._schedule_counter)
        def action():
            return [(event_type, payload)]
        heapq.heappush(self._scheduled, (deliver_at, cnt, action))

    def _capture_runtime_state(self):
        """Deep-copy unit state at the moment a future event is emitted."""
        import copy
        return {
            'player_units': copy.deepcopy([
                u.to_dict(current_hp=int(getattr(u, 'hp', 0))) for u in self.team_a
            ]),
            'opponent_units': copy.deepcopy([
                u.to_dict(current_hp=int(getattr(u, 'hp', 0))) for u in self.team_b
            ]),
        }

    # compatibility wrapper used by processors
    def schedule_event(self, deliver_at: float, action_callable):
        cnt = next(self._schedule_counter)
        heapq.heappush(self._scheduled, (deliver_at, cnt, action_callable))

    def _process_dot_for_team(
        self,
        team: List[CombatUnit],
        hp_list: Optional[List[int]] = None,
        time: float = 0.0,
        log: Optional[List[str]] = None,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        side: str = 'team_a'
    ):
        """Process damage over time effects for a single team (simulator-level).

        Implements canonical DoT tick emission, HP mutation via `emit_damage_over_time_tick`,
        and expiration via `emit_damage_over_time_expired`.
        """
        if hp_list is None:
            hp_list = [getattr(u, 'hp', 0) for u in team]
        if log is None:
            log = []

        for i, unit in enumerate(team):
            # Skip dead units - check both HP and _dead attribute for consistency
            if hp_list[i] <= 0 or getattr(unit, '_dead', False):
                continue

            if not hasattr(unit, 'effects') or not unit.effects:
                continue

            effects_to_remove = []
            for j, effect in enumerate(list(unit.effects)):
                if effect.get('type') != 'damage_over_time':
                    continue
                effect_id = _require_runtime_effect_id(
                    effect.get('id'), unit, 'damage_over_time', 'DoT tick/expiration'
                )
                next_tick = effect.get('next_tick_time', 0)
                if time < next_tick:
                    continue

                damage = effect.get('damage', 0)
                damage_type = effect.get('damage_type', 'physical')
                before_ticks = int(effect.get('ticks_remaining', 0))
                total_ticks = int(effect.get('total_ticks', before_ticks)) if before_ticks is not None else None
                tick_index = (total_ticks - before_ticks) + 1 if total_ticks and before_ticks is not None else None

                from .event_canonicalizer import emit_damage_over_time_tick, emit_damage_over_time_expired
                payload = emit_damage_over_time_tick(event_callback, unit, damage, damage_type=damage_type, side=side, timestamp=time, effect_id=effect_id, tick_index=tick_index, total_ticks=total_ticks)

                authoritative_hp = int(getattr(unit, 'hp', hp_list[i]))
                hp_list[i] = max(0, authoritative_hp)

                log.append(f"{unit.name} takes {int(damage)} {damage_type} damage from DoT")

                ticks_remaining = int(effect.get('ticks_remaining', 0)) - 1
                if ticks_remaining > 0:
                    interval = effect.get('interval', 1.0)
                    effect['ticks_remaining'] = ticks_remaining
                    effect['next_tick_time'] = time + interval
                else:
                    effects_to_remove.append((j, effect_id))

            for j, effect_id in reversed(effects_to_remove):
                try:
                    effect_count = len(unit.effects)
                    expected_effect = unit.effects[j]
                    expired = unit.effects.pop(j)
                    if len(unit.effects) != effect_count - 1 or any(
                        candidate is expected_effect for candidate in unit.effects
                    ):
                        raise RuntimeError(
                            "expired DoT effect remains after removal"
                        )
                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to remove expired DoT for unit={getattr(unit, 'id', None)} index={j}"
                    ) from exc

                # Emit expiration AFTER removal so game_state attached to this
                # event reflects post-expiry effect list.
                if not isinstance(expired, dict):
                    raise RuntimeError(
                        f"Expired DoT is not a mapping for unit={getattr(unit, 'id', None)} index={j}"
                    )
                emit_damage_over_time_expired(
                    event_callback,
                    unit,
                    effect_id,
                    unit_hp=hp_list[i],
                    side=side,
                    timestamp=time,
                )

        return

    def _process_effect_expiration_for_team(
        self,
        team: List[CombatUnit],
        hp_list: Optional[List[int]] = None,
        time: float = 0.0,
        log: Optional[List[str]] = None,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        side: str = 'team_a'
    ):
        """Process effect expiration for a single team (simulator-level).

        Checks for effects that have expired (current time >= expires_at) and:
        1. Reverts stat changes using applied_delta
        2. Emits effect_expired event
        3. Removes the effect from the unit
        """
        if hp_list is None:
            hp_list = [getattr(u, 'hp', 0) for u in team]
        if log is None:
            log = []

        for i, unit in enumerate(team):
            # Skip dead units - check both HP and _dead attribute for consistency
            if hp_list[i] <= 0 or getattr(unit, '_dead', False):
                continue

            if not hasattr(unit, 'effects') or not unit.effects:
                continue

            for effect in list(unit.effects):
                expires_at = effect.get('expires_at')
                if expires_at is None or time < expires_at:
                    continue

                # Validate and prepare the collection mutation before
                # reverting any stats or shields. A malformed sibling effect
                # must abort the lifecycle transition before state changes or
                # a canonical expiration event can be published.
                effect_id = effect.get('id')
                effect_id = _require_runtime_effect_id(
                    effect_id, unit, effect.get('type'), 'effect expiration'
                )
                try:
                    current_effects = list(unit.effects or [])
                    if any(not isinstance(candidate, dict) for candidate in current_effects):
                        raise TypeError("runtime effect collection contains a non-object entry")
                    updated_effects = [
                        candidate for candidate in current_effects
                        if candidate.get('id') != effect_id
                    ]
                    if len(updated_effects) == len(current_effects):
                        raise RuntimeError(f"expired effect id={effect_id!r} is not present in the collection")
                except Exception as exc:
                    raise RuntimeError(
                        f"Cannot prepare expiration removal for unit={getattr(unit, 'id', None)} effect={effect_id!r}"
                    ) from exc

                # Effect has expired - revert stat changes
                effect_type = effect.get('type')
                if effect_type in ('buff', 'debuff'):
                    stat = effect.get('stat')
                    applied_delta = effect.get('applied_delta', 0)
                    if stat and applied_delta:
                        # Revert the stat change by subtracting the applied_delta
                        if stat == 'hp':
                            old_hp = getattr(unit, stat, 0)
                            new_hp = max(0, old_hp - applied_delta)
                            from .event_canonicalizer import apply_effect_expiration_mutation
                            apply_effect_expiration_mutation(unit, stat, new_hp)
                            hp_list[i] = new_hp  # Update HP list
                            log.append(f"{unit.name} stat {stat} reverted by {-applied_delta} (effect expired)")
                        elif stat == 'max_hp':
                            old_max_hp = int(getattr(unit, 'max_hp', 0) or 0)
                            old_hp = int(getattr(unit, 'hp', 0) or 0)
                            new_max_hp = max(0, old_max_hp - applied_delta)
                            if old_max_hp > 0:
                                new_hp = min(new_max_hp, int(round(old_hp * new_max_hp / old_max_hp)))
                            else:
                                new_hp = min(new_max_hp, old_hp)
                            from .event_canonicalizer import apply_effect_expiration_mutation
                            apply_effect_expiration_mutation(unit, stat, new_max_hp, new_hp)
                            hp_list[i] = new_hp
                            log.append(f"{unit.name} stat {stat} reverted by {-applied_delta} (effect expired)")
                        else:
                            old_val = getattr(unit, stat, 0)
                            new_val = old_val - applied_delta
                            setattr(unit, stat, new_val)
                            log.append(f"{unit.name} stat {stat} reverted by {-applied_delta} (effect expired)")
                elif effect_type == 'shield':
                    applied_amount = effect.get('applied_amount', 0)
                    if applied_amount:
                        old_shield = getattr(unit, 'shield', 0)
                        new_shield = max(0, old_shield - applied_amount)
                        setattr(unit, 'shield', new_shield)
                        log.append(f"{unit.name} shield reverted by {-applied_amount} (effect expired)")

                # Remove THIS expired effect only after all state reversion
                # calculations have succeeded, but before the event is emitted.
                try:
                    unit.effects = updated_effects
                    if any(
                        isinstance(candidate, dict) and candidate.get('id') == effect_id
                        for candidate in (unit.effects or [])
                    ):
                        raise RuntimeError("expired effect remains after removal")
                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to remove expired effect for unit={getattr(unit, 'id', None)} effect={effect_id!r}"
                    ) from exc

                # Emit this expiration AFTER this effect mutation so event
                # game_state is post-expiry for this exact effect only.
                from .event_canonicalizer import emit_effect_expired
                emit_effect_expired(
                    event_callback,
                    unit,
                    effect_id,
                    unit_hp=hp_list[i],
                    side=side,
                    timestamp=time,
                    effect_type=effect_type,
                    stat=effect.get('stat'),
                    applied_delta=effect.get('applied_delta'),
                    applied_amount=effect.get('applied_amount'),
                )

        return

    def _apply_per_round_hp_buff(
        self,
        unit: CombatUnit,
        hp_mirror: List[int],
        unit_index: int,
        amount: int,
        side: str,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        log: List[str],
    ) -> None:
        """Apply one start-of-combat HP buff before committing its mirror.

        Canonical HP mutation must succeed before the simulator mirror or
        success log advances. This keeps a rejected heal from creating a
        replay-visible state that differs from the live unit.
        """
        old_hp = int(hp_mirror[unit_index])
        if event_callback is None:
            # Preserve direct callers that intentionally use the processor
            # without an event sink.
            hp_mirror[unit_index] = min(int(unit.max_hp), old_hp + int(amount))
            log.append(f"{unit.name} {amount:+d} HP (per round buff)")
            return

        from .event_canonicalizer import emit_heal, _set_and_verify_canonical_hp

        try:
            payload = emit_heal(
                event_callback,
                unit,
                amount,
                source=None,
                side=side,
                timestamp=0.0,
                current_hp=old_hp,
            )
        except Exception:
            # The canonical setter can fail after a partial write, and the
            # event sink can fail after the setter succeeds. Restore the unit
            # when needed; leave the mirror and log at their pre-operation
            # values until the canonical operation has completed.
            try:
                actual_hp = int(getattr(unit, 'hp'))
            except Exception:
                actual_hp = old_hp
            if actual_hp != old_hp:
                _set_and_verify_canonical_hp(unit, old_hp)
                if int(getattr(unit, 'hp')) != old_hp:
                    raise RuntimeError(
                        f"Failed to roll back per-round HP buff for unit={getattr(unit, 'id', None)}"
                    )
            raise

        if payload is None:
            # Keep the mirror aligned if the canonical emitter suppresses an
            # event after a successful mutation (for example, a late death).
            hp_mirror[unit_index] = int(getattr(unit, 'hp'))
            return

        hp_mirror[unit_index] = int(payload['post_hp'])
        log.append(f"{unit.name} {amount:+d} HP (per round buff)")

    def _process_per_round_hp_buffs_for_team(
        self,
        team: List[CombatUnit],
        hp_mirror: List[int],
        side: str,
        round_number: int,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        log: List[str],
    ) -> None:
        """Process start-of-combat per-round HP buffs for one team."""
        for unit_index, unit in enumerate(team):
            for effect in getattr(unit, 'effects', []):
                if effect.get('type') != 'per_round_buff' or effect.get('stat') != 'hp':
                    continue
                value = effect.get('value', 0)
                if effect.get('is_percentage', False):
                    amount = int(unit.max_hp * (value / 100.0) * round_number)
                else:
                    amount = int(value * round_number)
                self._apply_per_round_hp_buff(
                    unit,
                    hp_mirror,
                    unit_index,
                    amount,
                    side,
                    event_callback,
                    log,
                )

    def _process_modular_trigger_for_team(
        self,
        trigger,
        team: List[CombatUnit],
        enemy_team: List[CombatUnit],
        hp_mirror: List[int],
        side: str,
        time: float,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        **extra_context,
    ) -> None:
        """Dispatch one canonical modular trigger for one combat side."""
        if not team:
            return

        unit_indices = {
            getattr(unit, 'id', None): index
            for index, unit in enumerate(team)
        }
        context = {
            'all_units': team,
            'ally_units': team,
            'enemy_units': enemy_team,
            'current_time': time,
            'side': side,
            'hp_mirror': hp_mirror,
            'unit_indices': unit_indices,
            **extra_context,
        }
        self.modular_effect_processor.process_trigger(trigger, context, event_callback)

    def _deliver_scheduled_events(self, sink):
        current = getattr(self, '_current_time', 0.0)
        while self._scheduled and self._scheduled[0][0] <= current:
            _, _, action = heapq.heappop(self._scheduled)
            results = action()
            if isinstance(results, dict):
                results = [('scheduled_event', results)]
            if results:
                for ev_type, ev_payload in results:
                    sink.emit(ev_type, ev_payload)

    def simulate(self, team_a, team_b, event_callback=None, round_number: int = 1, skip_per_round_buffs: bool = False):
        # Prepare event callback
        if event_callback is None:
            def noop(*a, **k):
                return
            event_callback = noop

        # initialize teams and HP mirrors
        self.team_a = list(team_a)
        self.team_b = list(team_b)
        self.a_hp = [int(getattr(u, 'hp', 0)) for u in self.team_a]
        self.b_hp = [int(getattr(u, 'hp', 0)) for u in self.team_b]
        self.modular_effect_processor.reset_combat_state()
        # (mana mirrors are managed by CombatState)

        # ensure unit runtime fields exist
        for u in self.team_a + self.team_b:
            if not hasattr(u, 'mana'):
                u.mana = 0
            if not hasattr(u, 'last_attack_time'):
                u.last_attack_time = 0.0

        log = []
        time = 0.0
        sink = _EventSink(self, event_callback)
        # route events through sink.emit so seq/event_id and scheduling are applied
        proc_cb = sink.emit

        # create combat state snapshot helper
        self._combat_state = CombatState(self.team_a, self.team_b)

        # Passive initialization is the only start-of-combat effect path. It
        # runs before the first attack and never invokes the skill executor.
        self.passive_processor.initialize(self.team_a, self.team_b, proc_cb, timestamp=0.0)

        # Canonical modular per-round records are dispatched at the same
        # start-of-combat lifecycle point as legacy per-round records, before
        # the first animation/state snapshot.
        from .modular_effect_processor import TriggerType
        self._process_modular_trigger_for_team(
            TriggerType.PER_ROUND,
            self.team_a,
            self.team_b,
            self.a_hp,
            'team_a',
            0.0,
            proc_cb,
            round_number=round_number,
        )
        self._process_modular_trigger_for_team(
            TriggerType.PER_ROUND,
            self.team_b,
            self.team_a,
            self.b_hp,
            'team_b',
            0.0,
            proc_cb,
            round_number=round_number,
        )

        # Apply per-round HP buffs through the same canonical path for both
        # teams. The separate skip_per_round_buffs contract remains tracked by
        # DEF-235 and is intentionally unchanged here.
        self._process_per_round_hp_buffs_for_team(
            self.team_a,
            self.a_hp,
            'team_a',
            round_number,
            proc_cb,
            log,
        )
        self._process_per_round_hp_buffs_for_team(
            self.team_b,
            self.b_hp,
            'team_b',
            round_number,
            proc_cb,
            log,
        )

        # emit animation start
        proc_cb('animation_start', {'timestamp': 0.0})

        winner = None
        # Main loop
        while time < self.timeout:
            self._current_time = time

            # Per-second buffs and regen
            if not skip_per_round_buffs:
                self._process_modular_trigger_for_team(
                    TriggerType.PER_SECOND,
                    self.team_a,
                    self.team_b,
                    self.a_hp,
                    'team_a',
                    time,
                    proc_cb,
                )
                self._process_modular_trigger_for_team(
                    TriggerType.PER_SECOND,
                    self.team_b,
                    self.team_a,
                    self.b_hp,
                    'team_b',
                    time,
                    proc_cb,
                )
                self._process_per_second_buffs(self.team_a, self.team_b, self.a_hp, self.b_hp, time, log, proc_cb)
            self._process_regeneration(self.team_a, self.team_b, self.a_hp, self.b_hp, time, log, self.dt, proc_cb)

            # Deliver any scheduled events due now
            self._deliver_scheduled_events(sink)

            # A team can be wiped by scheduled damage/DoT between attack
            # phases. End immediately instead of advancing empty ticks until
            # timeout and emitting meaningless mana events.
            team_a_alive = any(hp > 0 for hp in self.a_hp)
            team_b_alive = any(hp > 0 for hp in self.b_hp)
            if not team_a_alive or not team_b_alive:
                # The surviving team wins. If scheduled effects wipe both
                # teams at the same timestamp, keep the legacy deterministic
                # tie-breaker instead of continuing until timeout.
                winner = 'team_a' if team_a_alive or not team_b_alive else 'team_b'
                break

            # Process damage-over-time effects for both teams (emit ticks and expirations)
            self._process_dot_for_team(self.team_a, self.a_hp, time, log, proc_cb, 'team_a')
            self._process_dot_for_team(self.team_b, self.b_hp, time, log, proc_cb, 'team_b')

            # Process effect expiration for both teams (revert stats and emit expirations)
            self._process_effect_expiration_for_team(self.team_a, self.a_hp, time, log, proc_cb, 'team_a')
            self._process_effect_expiration_for_team(self.team_b, self.b_hp, time, log, proc_cb, 'team_b')

            # Emit a state snapshot for reconstructors and replay tests
            if getattr(self, '_combat_state', None) is not None:
                snap = self._combat_state.get_snapshot_data(time)
                proc_cb('state_snapshot', snap)

            # Team A attacks
            winner = self._process_team_attacks(self.team_a, self.team_b, self.a_hp, self.b_hp, time, log, proc_cb, 'team_a')
            if winner:
                break

            # Team B attacks
            winner = self._process_team_attacks(self.team_b, self.team_a, self.b_hp, self.a_hp, time, log, proc_cb, 'team_b')
            if winner:
                break

            # advance time
            time = round(time + float(self.dt), 10)

        # Final delivery of any scheduled events up to timeout
        self._current_time = time
        self._deliver_scheduled_events(sink)

        # Flush remaining scheduled events present at this point only.
        # Some actions may schedule new events; process only the snapshot
        # to avoid infinite rescheduling loops during finalization.
        pending = list(self._scheduled)
        # Clear the scheduled heap so any new scheduled events are left for
        # the normal simulator lifecycle (or external inspection).
        self._scheduled = []
        for deliver_at, _, action in pending:
            # Advance current time to the delivery time to avoid re-scheduling
            # due to floating-point timestamps being slightly greater than
            # the simulator current time. Let errors propagate so callers
            # can see problems during finalization.
            self._current_time = deliver_at
            results = action()
            if isinstance(results, dict):
                results = [('scheduled_event', results)]
            if results:
                for ev_type, ev_payload in results:
                    sink.emit(ev_type, ev_payload)

        # Build summary
        team_a_survivors = sum(1 for hp in self.a_hp if hp > 0)
        team_b_survivors = sum(1 for hp in self.b_hp if hp > 0)
        # Debug: expose final authoritative HP arrays for replay verification
        print(f"[SIM FINAL HP] a_hp={self.a_hp} b_hp={self.b_hp}")
        return {'winner': winner or 'team_a', 'duration': time, 'team_a_survivors': team_a_survivors, 'team_b_survivors': team_b_survivors, 'log': log, 'timeout': time >= self.timeout}


# Provide test-suite compatible EventSink symbol
def _EventSink(simulator, collector):
    return _DispatcherEventSink(simulator, collector)
