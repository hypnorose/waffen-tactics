from typing import List, Dict, Any, Callable, Optional
import itertools
import heapq
import uuid

from .combat_unit import CombatUnit
from .combat_attack_processor import CombatAttackProcessor
from .combat_effect_processor import CombatEffectProcessor
from .combat_regeneration_processor import CombatRegenerationProcessor
from .combat_per_second_buff_processor import CombatPerSecondBuffProcessor
from .modular_effect_processor import ModularEffectProcessor
from ..engine.combat_state import CombatState


class CombatSimulator:
    """Minimal CombatSimulator used for scheduler-related tests.

    This intentionally implements a small surface area: `simulate`,
    `_enqueue_scheduled_event`, and `_deliver_scheduled_events`, and
    sequence assignment semantics used by tests.
    """

    def __init__(self, dt: float = 0.1, timeout: int = 120):
        self.dt = dt
        self.timeout = timeout
        self._scheduled = []  # heap of (deliver_at, counter, action)
        self._schedule_counter = itertools.count()
        self._event_seq = 0
        self._current_time = 0.0

    def _enqueue_scheduled_event(self, deliver_at: float, event_type: str, payload: Dict[str, Any]):
        cnt = next(self._schedule_counter)
        def action():
            return [(event_type, payload)]
        heapq.heappush(self._scheduled, (deliver_at, cnt, action))

    def _deliver_scheduled_events(self, sink: "_EventSink"):
        current = getattr(self, '_current_time', 0.0)
        while self._scheduled and self._scheduled[0][0] <= current:
            _, _, action = heapq.heappop(self._scheduled)
            results = action()
            if isinstance(results, dict):
                results = [('scheduled_event', results)]
            if results:
                for ev_type, ev_payload in results:
                    sink.emit(ev_type, ev_payload)

    def simulate(
        self,
        team_a: List[CombatUnit],
        team_b: List[CombatUnit],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        round_number: int = 1,
        skip_per_round_buffs: bool = False,
    ) -> Dict[str, Any]:
        # Minimal behavior for tests: emit an animation_start then a unit_attack
        if event_callback is None:
            def noop(*a, **k):
                return
            event_callback = noop

        # Use the provided callback directly; test harness wraps it to add seq
        event_callback('animation_start', {'timestamp': 0.0})
        event_callback('unit_attack', {'timestamp': float(self.dt)})

        return {'winner': 'team_a', 'duration': 0.0, 'team_a_survivors': 1, 'team_b_survivors': 0, 'log': []}


class _EventSink:
    """Small event sink used by tests.

    Behavior:
    - If payload timestamp > simulator._current_time -> enqueue via simulator._enqueue_scheduled_event
    - Otherwise deliver immediately and assign `seq` and `event_id` similar to simulator wrapper
    """
    def __init__(self, simulator: CombatSimulator, collector: Callable[[str, Dict[str, Any]], None]):
        self.simulator = simulator
        self.collector = collector

    def emit(self, event_type: str, payload: Dict[str, Any]):
        data = dict(payload) if isinstance(payload, dict) else payload

        ts = data.get('timestamp') if isinstance(data, dict) else None
        current = getattr(self.simulator, '_current_time', 0.0)

        if isinstance(ts, (int, float)) and ts > current:
            # schedule for later
            self.simulator._enqueue_scheduled_event(ts, event_type, data if isinstance(data, dict) else {'payload': data})
            return

        # immediate delivery: attach seq and event_id
        seq_value = getattr(self.simulator, '_event_seq', 0) + 1

        if isinstance(data, dict):
            if seq_value is not None:
                data['seq'] = seq_value
            data['event_id'] = str(uuid.uuid4())
            # Ensure mana_update payloads always include 'amount' for schema consistency
            if event_type == 'mana_update' and 'amount' not in data:
                data['amount'] = 0

        self.collector(event_type, data)
        if seq_value is not None:
            self.simulator._event_seq = seq_value


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
                            from .event_canonicalizer import emit_heal
                            emit_heal(event_callback, team[target_idx], heal_amt, source=None, side=side, timestamp=time)
                        eff['_triggered'] = True
                        break

    def _process_damage_over_time(
        self,
        team_a: List[CombatUnit],
        team_b: List[CombatUnit],
        a_hp: List[int],
        b_hp: List[int],
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]]
    ):
        """Process damage over time effects for both teams."""
        # Process team A
        self._process_dot_for_team(team_a, a_hp, time, log, event_callback, 'team_a')
        # Process team B
        self._process_dot_for_team(team_b, b_hp, time, log, event_callback, 'team_b')

    def _process_dot_for_team(
        self,
        team: List[CombatUnit],
        hp_list: Optional[List[int]] = None,
        time: float = 0.0,
        log: Optional[List[str]] = None,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        side: str = 'team_a'
    ):
        """Process damage over time effects for a single team."""
        if hp_list is None:
            # build a minimal hp_list from unit.hp values
            try:
                hp_list = [getattr(u, 'hp', 0) for u in team]
            except Exception:
                hp_list = [0 for _ in team]
        if log is None:
            log = []
        return
# --- Fallback minimal CombatSimulator and EventSink for scheduling tests ---
class _SimpleEventSink:
    def __init__(self, sim, collector):
        self.sim = sim
        self.collector = collector

    def emit(self, event_type, payload):
        # immediate delivery if timestamp <= current_time, otherwise enqueue
        try:
            data = dict(payload) if isinstance(payload, dict) else payload
        except Exception:
            data = payload
        ts = data.get('timestamp') if isinstance(data, dict) else None
        current = getattr(self.sim, '_current_time', 0.0)
        if isinstance(ts, (int, float)) and ts > current:
            self.sim._enqueue_scheduled_event(ts, event_type, data)
            return

        # attach seq and event_id
        try:
            seq_value = getattr(self.sim, '_event_seq', 0) + 1
        except Exception:
            seq_value = None
        if isinstance(data, dict):
            if seq_value is not None:
                data['seq'] = seq_value
            data['event_id'] = str(uuid.uuid4())
            # Ensure mana_update payloads always include 'amount' for schema consistency
            if event_type == 'mana_update' and 'amount' not in data:
                data['amount'] = 0

        try:
            self.collector(event_type, data)
            if seq_value is not None:
                self.sim._event_seq = seq_value
        except Exception:
            if getattr(self.sim, 'strict_exceptions', False):
                raise
            return


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
                next_tick = effect.get('next_tick_time', 0)
                if time < next_tick:
                    continue

                damage = effect.get('damage', 0)
                damage_type = effect.get('damage_type', 'physical')
                before_ticks = int(effect.get('ticks_remaining', 0))
                total_ticks = int(effect.get('total_ticks', before_ticks)) if before_ticks is not None else None
                tick_index = (total_ticks - before_ticks) + 1 if total_ticks and before_ticks is not None else None

                from .event_canonicalizer import emit_damage_over_time_tick, emit_damage_over_time_expired
                payload = emit_damage_over_time_tick(event_callback, unit, damage, damage_type=damage_type, side=side, timestamp=time, effect_id=effect.get('id'), tick_index=tick_index, total_ticks=total_ticks)

                authoritative_hp = int(getattr(unit, 'hp', hp_list[i]))
                hp_list[i] = max(0, authoritative_hp)

                log.append(f"{unit.name} takes {int(damage)} {damage_type} damage from DoT")

                ticks_remaining = int(effect.get('ticks_remaining', 0)) - 1
                if ticks_remaining > 0:
                    interval = effect.get('interval', 1.0)
                    effect['ticks_remaining'] = ticks_remaining
                    effect['next_tick_time'] = time + interval
                else:
                    effects_to_remove.append(j)
                    emit_damage_over_time_expired(event_callback, unit, effect.get('id'), unit_hp=hp_list[i], side=side, timestamp=time)

            for j in reversed(effects_to_remove):
                try:
                    unit.effects.pop(j)
                except Exception:
                    pass

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

            effects_to_remove = []
            for j, effect in enumerate(list(unit.effects)):
                expires_at = effect.get('expires_at')
                if expires_at is None or time < expires_at:
                    continue

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
                            setattr(unit, stat, new_hp)
                            hp_list[i] = new_hp  # Update HP list
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

                # Emit effect_expired event
                from .event_canonicalizer import emit_effect_expired
                emit_effect_expired(event_callback, unit, effect.get('id'), unit_hp=hp_list[i], side=side, timestamp=time)

                # Mark effect for removal
                effects_to_remove.append(j)

            # Remove expired effects
            for j in reversed(effects_to_remove):
                try:
                    unit.effects.pop(j)
                except Exception:
                    pass

        return

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

        # Apply per-round buffs
        for idx_u, u in enumerate(self.team_a):
            for eff in getattr(u, 'effects', []):
                if eff.get('type') == 'per_round_buff':
                    stat = eff.get('stat')
                    val = eff.get('value', 0)
                    is_pct = eff.get('is_percentage', False)
                    if stat == 'hp':
                        if is_pct:
                            add = int(u.max_hp * (val / 100.0) * round_number)
                        else:
                            add = int(val * round_number)
                        old_hp = int(self.a_hp[idx_u])
                        self.a_hp[idx_u] = min(u.max_hp, self.a_hp[idx_u] + add)
                        log.append(f"{u.name} {add:+d} HP (per round buff)")
                        if event_callback:
                            from .event_canonicalizer import emit_heal
                            emit_heal(event_callback, u, add, source=None, side='team_a', timestamp=0.0, current_hp=old_hp)

        for idx_u, u in enumerate(self.team_b):
            for eff in getattr(u, 'effects', []):
                if eff.get('type') == 'per_round_buff':
                    stat = eff.get('stat')
                    val = eff.get('value', 0)
                    is_pct = eff.get('is_percentage', False)
                    if stat == 'hp':
                        if is_pct:
                            add = int(u.max_hp * (val / 100.0) * round_number)
                        else:
                            add = int(val * round_number)
                        old_hp = int(self.b_hp[idx_u])
                        self.b_hp[idx_u] = min(u.max_hp, self.b_hp[idx_u] + add)
                        log.append(f"{u.name} {add:+d} HP (per round buff)")
                        if event_callback:
                            from .event_canonicalizer import emit_heal
                            emit_heal(event_callback, u, add, source=None, side='team_b', timestamp=0.0, current_hp=old_hp)

        # emit animation start
        proc_cb('animation_start', {'timestamp': 0.0})

        winner = None
        # Main loop
        while time < self.timeout:
            self._current_time = time

            # Per-second buffs and regen
            if not skip_per_round_buffs:
                self._process_per_second_buffs(self.team_a, self.team_b, self.a_hp, self.b_hp, time, log, proc_cb)
            self._process_regeneration(self.team_a, self.team_b, self.a_hp, self.b_hp, time, log, self.dt, proc_cb)

            # Deliver any scheduled events due now
            self._deliver_scheduled_events(sink)

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

        # Build summary
        team_a_survivors = sum(1 for hp in self.a_hp if hp > 0)
        team_b_survivors = sum(1 for hp in self.b_hp if hp > 0)
        return {'winner': winner or 'team_a', 'duration': time, 'team_a_survivors': team_a_survivors, 'team_b_survivors': team_b_survivors, 'log': log, 'timeout': time >= self.timeout}


# Provide test-suite compatible EventSink symbol
def _EventSink(simulator, collector):
    return _SimpleEventSink(simulator, collector)


