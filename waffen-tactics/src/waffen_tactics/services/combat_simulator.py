"""
CombatSimulator class - handles combat simulation logic
"""
from typing import List, Dict, Any, Callable, Optional
import uuid

from .combat_attack_processor import CombatAttackProcessor
from .combat_effect_processor import CombatEffectProcessor
from .combat_regeneration_processor import CombatRegenerationProcessor
from .combat_win_conditions import CombatWinConditionsProcessor
from .combat_per_second_buff_processor import CombatPerSecondBuffProcessor
from .modular_effect_processor import ModularEffectProcessor, TriggerType
from .combat_unit import CombatUnit
from .event_canonicalizer import emit_mana_update, emit_stat_buff, emit_damage_over_time_tick, emit_mana_change


class CombatSimulator(
    CombatAttackProcessor,
    CombatEffectProcessor,
    CombatRegenerationProcessor,
    CombatWinConditionsProcessor,
    CombatPerSecondBuffProcessor
):
    """Shared combat simulator using tick-based attack speed system"""

    def __init__(self, dt: float = 0.1, timeout: int = 120):
        """
        Args:
            dt: Time step in seconds (0.1 = 100ms ticks)
            timeout: Max combat duration in seconds
        """
        # Initialize modular effect processor first
        self.modular_effect_processor = ModularEffectProcessor()
        
        # Initialize parent classes with modular effect processor
        super().__init__(self.modular_effect_processor)
        
        self.dt = dt
        self.timeout = timeout
        self._event_seq = 0
        # Track last seen mana per unit id so we can compute mana deltas
        # for emitted `mana_update` events when the payload only contains
        # `current_mana` (e.g. skill casts / snapshots). This keeps event
        # payloads consistent for tests and downstream consumers.
        self._last_mana = {}

    def simulate(
        self,
        team_a: List['CombatUnit'],
        team_b: List['CombatUnit'],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        round_number: int = 1,
        skip_per_round_buffs: bool = False
    ) -> Dict[str, Any]:
        """
        Simulate combat between two teams

        Args:
            team_a: First team units
            team_b: Second team units
            event_callback: Optional callback for combat events (type, data)
            round_number: Current round number for per-round buffs

        Returns:
            Dict with winner, duration, survivors, log
        """
        # Store teams for use in _finish_combat
        self.team_a = team_a
        self.team_b = team_b
        
        # Track HP separately to avoid mutating input units
        a_hp = [u.hp for u in team_a]
        b_hp = [u.hp for u in team_b]
        self.a_hp = a_hp
        self.b_hp = b_hp
        log = []

        # Wrap event_callback to add seq
        if event_callback:
            original_callback = event_callback
            def wrapped_callback(event_type, data):
                # Prepare a sequence value to attach to the payload, but only
                # increment the simulator's global seq after the callback
                # completes successfully. This prevents the seq counter from
                # advancing when the downstream consumer fails to receive the
                # event (which was causing snapshot mismatches).
                try:
                    seq_value = self._event_seq + 1
                except Exception:
                    seq_value = None

                # copy dicts to avoid mutating caller-owned objects
                if isinstance(data, dict):
                    payload = dict(data)
                else:
                    payload = data

                if isinstance(payload, dict):
                    if seq_value is not None:
                        payload['seq'] = seq_value
                    payload['event_id'] = str(uuid.uuid4())

                # If this is a mana update that lacks an 'amount' field,
                # attempt to compute the delta from last seen mana so
                # downstream consumers receive a consistent payload
                # containing both 'current_mana' and 'amount'. This is
                # especially useful for skill-cast or snapshot emissions
                # that only include current_mana.
                try:
                    if isinstance(payload, dict) and event_type == 'mana_update' and 'amount' not in payload:
                        unit_id = payload.get('unit_id')
                        # Determine current mana from payload or live unit
                        current = payload.get('current_mana')
                        if current is None and unit_id and hasattr(self, 'team_a') and hasattr(self, 'team_b'):
                            for u in self.team_a + self.team_b:
                                if getattr(u, 'id', None) == unit_id:
                                    current = getattr(u, 'mana', None)
                                    break
                        prev = None
                        if unit_id is not None:
                            prev = self._last_mana.get(unit_id)
                        # If we can compute a numeric non-zero delta, include it
                        if prev is not None and current is not None:
                            try:
                                delta = int(current - prev)
                                if delta != 0:
                                    payload['amount'] = delta
                            except Exception:
                                # ignore failures computing delta
                                pass
                except Exception:
                    # best-effort; don't break event emission
                    pass

                # Ensure any emitted event that refers to a unit uses the
                # simulator's authoritative HP lists (`self.a_hp` / `self.b_hp`).
                # This prevents codepaths that emit payloads using local
                # copies (e.g. `target_hp_list`) from sending stale HP values
                # that disagree with the soon-to-be-emitted `state_snapshot`.
                if isinstance(payload, dict):
                    target_id_ref = payload.get('target_id') or payload.get('unit_id')
                    if target_id_ref and hasattr(self, 'team_a') and hasattr(self, 'team_b'):
                        for i, u in enumerate(self.team_a + self.team_b):
                            if u.id != target_id_ref:
                                continue
                            if i < len(self.team_a):
                                hp_list = self.a_hp
                                local_idx = i
                            else:
                                hp_list = self.b_hp
                                local_idx = i - len(self.team_a)
                            try:
                                authoritative_hp = int(hp_list[local_idx])
                            except Exception:
                                authoritative_hp = hp_list[local_idx]

                            # Normalize common payload field names to authoritative value
                            # ONLY set target_hp/unit_hp if not already present in payload.
                            # Event handlers (like damage effects) may have already set these
                            # to the correct post-action HP, which we should preserve.
                            if 'target_id' in payload and 'target_hp' not in payload:
                                payload['target_hp'] = authoritative_hp
                            if 'unit_id' in payload and 'unit_hp' not in payload:
                                payload['unit_hp'] = authoritative_hp

                            # NOTE: Do NOT overwrite 'old_hp' or 'new_hp' fields.
                            # These are intentionally set by event handlers to show
                            # HP transitions (before/after) and should not be modified.
                            # Only set 'target_hp' and 'unit_hp' if missing from payload.

                            break
                # Try to emit the event. Only update the simulator seq if the
                # downstream callback succeeds.
                try:
                    # Suppress emitting mana_update snapshot events that do not
                    # represent an actual mana delta. These snapshot-only
                    # events (they contain `current_mana` but no computed
                    # `amount`) would otherwise show up as zero-delta
                    # mana_update events and break regen tests that expect
                    # only meaningful mana changes.
                    if event_type == 'mana_update' and isinstance(payload, dict) and 'current_mana' in payload and 'amount' not in payload:
                        return

                    original_callback(event_type, payload)
                except Exception as e:
                    # Log to stdout/stderr so the test harness can see failures
                    try:
                        print(f"[EVENT EMIT ERROR] type={event_type} seq={seq_value} error={e}")
                    except Exception:
                        pass
                    # Do not advance self._event_seq on failure — this keeps
                    # seqs tightly coupled to successfully-delivered events.
                    return

                # If we got here, the event was delivered successfully —
                # advance the simulator sequence counter to the value used.
                try:
                    if seq_value is not None:
                        self._event_seq = seq_value
                    else:
                        self._event_seq += 1
                except Exception:
                    # Best-effort: ignore if incrementing fails
                    pass

                # Update last-seen mana after successful delivery so future
                # mana_update events can compute deltas.
                try:
                    if isinstance(payload, dict) and payload.get('unit_id') and event_type == 'mana_update':
                        uid = payload.get('unit_id')
                        cur = payload.get('current_mana')
                        # If current_mana missing, attempt to read from unit
                        if cur is None and hasattr(self, 'team_a') and hasattr(self, 'team_b'):
                            for u in self.team_a + self.team_b:
                                if getattr(u, 'id', None) == uid:
                                    cur = getattr(u, 'mana', None)
                                    break
                        if cur is not None:
                            try:
                                self._last_mana[uid] = int(cur)
                            except Exception:
                                self._last_mana[uid] = cur
                except Exception:
                    pass

            event_callback = wrapped_callback

        # Initialize mana tracking for all units at combat start
        # This allows mana_update events to compute deltas properly
        for u in team_a + team_b:
            if hasattr(u, 'mana') and hasattr(u, 'id'):
                self._last_mana[u.id] = u.mana

        # Reset modular effect processor for new combat
        self.modular_effect_processor.reset_combat_state()

        # Reset per-unit transient flags used during simulation (e.g. death processed)
        for u in team_a + team_b:
            if hasattr(u, '_death_processed'):
                u._death_processed = False

        time = 0.0
        last_full_second = -1

        # Apply per-round buffs at start of combat
        if not skip_per_round_buffs:
            self._process_per_round_buffs(team_a, team_b, a_hp, b_hp, time, log, event_callback, round_number)

            # Process PER_ROUND triggers with modular effect processor
            for unit in team_a + team_b:
                if a_hp[team_a.index(unit)] > 0 if unit in team_a else b_hp[team_b.index(unit)] > 0:
                    context = {
                        'current_unit': unit,
                        'all_units': team_a + team_b,
                        'ally_units': team_a if unit in team_a else team_b,
                        'enemy_units': team_b if unit in team_a else team_a,
                        'current_time': time,
                        'side': 'team_a' if unit in team_a else 'team_b',
                        'round_number': round_number
                    }
                    self.modular_effect_processor.process_trigger(
                        TriggerType.PER_ROUND,
                        context,
                        event_callback
                    )

        # Debug log
        import logging
        logger = logging.getLogger('waffen_tactics')
        logger.info(f"[COMBAT] Starting simulation with team_a: {[u.name for u in team_a]}, team_b: {[u.name for u in team_b]}")
        logger.info(f"[COMBAT] Team A effects: {[u.effects for u in team_a]}")
        logger.info(f"[COMBAT] Team B effects: {[u.effects for u in team_b]}")

        while time < self.timeout:
            time += self.dt

            # Process attacks for both teams
            winner = self._process_team_attacks(team_a, team_b, a_hp, b_hp, time, log, event_callback, 'team_a')
            if winner:
                return self._finish_combat(winner, time, a_hp, b_hp, log, team_a)

            # Sync HP lists from unit.hp after team_a attacks (canonical emitters may have updated unit.hp)
            for i, u in enumerate(team_a):
                new_hp = max(0, int(getattr(u, 'hp', a_hp[i])))
                a_hp[i] = new_hp
            for i, u in enumerate(team_b):
                new_hp = max(0, int(getattr(u, 'hp', b_hp[i])))
                b_hp[i] = new_hp

            winner = self._process_team_attacks(team_b, team_a, b_hp, a_hp, time, log, event_callback, 'team_b')
            if winner:
                return self._finish_combat(winner, time, a_hp, b_hp, log, team_b)

            # Sync HP lists from unit.hp after team_b attacks (canonical emitters may have updated unit.hp)
            for i, u in enumerate(team_a):
                new_hp = max(0, int(getattr(u, 'hp', a_hp[i])))
                a_hp[i] = new_hp
            for i, u in enumerate(team_b):
                new_hp = max(0, int(getattr(u, 'hp', b_hp[i])))
                b_hp[i] = new_hp

            # Apply HP regeneration
            self._process_regeneration(team_a, team_b, a_hp, b_hp, time, log, self.dt, event_callback)

            # Check win conditions
            winner = self._check_win_conditions(a_hp, b_hp)
            if winner:
                logger.info(f"[COMBAT] Win condition met at {time:.2f}s: {winner}, a_hp={a_hp}, b_hp={b_hp}")
                return self._finish_combat(winner, time, a_hp, b_hp, log, team_a if winner == "team_a" else team_b)

            # Per-second buffs: apply once per full second
            current_second = int(time)
            buffs_processed = False
            if current_second != last_full_second:
                last_full_second = current_second
                self._process_per_second_buffs(team_a, team_b, a_hp, b_hp, time, log, event_callback)
                buffs_processed = True

                # Process PER_SECOND triggers with modular effect processor
                for unit in team_a + team_b:
                    if a_hp[team_a.index(unit)] > 0 if unit in team_a else b_hp[team_b.index(unit)] > 0:
                        context = {
                            'current_unit': unit,
                            'all_units': team_a + team_b,
                            'ally_units': team_a if unit in team_a else team_b,
                            'enemy_units': team_b if unit in team_a else team_a,
                            'current_time': time,
                            'side': 'team_a' if unit in team_a else 'team_b'
                        }
                        self.modular_effect_processor.process_trigger(
                            TriggerType.PER_SECOND,
                            context,
                            event_callback
                        )

            # Process damage over time effects
            self._process_damage_over_time(team_a, team_b, a_hp, b_hp, time, log, event_callback)

            # Send state snapshot every second (after all processing)
            if buffs_processed and event_callback:
                # CRITICAL: Sync HP lists from unit.hp before snapshot
                # Canonical emitters (emit_damage, emit_unit_heal) mutate unit.hp directly.
                # Ensure hp lists reflect the authoritative unit.hp values.
                for i, u in enumerate(team_a):
                    new_hp = max(0, int(getattr(u, 'hp', a_hp[i])))
                    if getattr(u, 'id', None) == 'mrozu' and new_hp != a_hp[i]:
                        print(f"[PRE-SNAPSHOT SYNC] mrozu a_hp[{i}]: {a_hp[i]} -> {new_hp} (unit.hp={u.hp})")
                    a_hp[i] = new_hp
                for i, u in enumerate(team_b):
                    new_hp = max(0, int(getattr(u, 'hp', b_hp[i])))
                    if getattr(u, 'id', None) == 'mrozu' and new_hp != b_hp[i]:
                        print(f"[PRE-SNAPSHOT SYNC] mrozu b_hp[{i}]: {b_hp[i]} -> {new_hp} (unit.hp={u.hp})")
                    b_hp[i] = new_hp

                # Build snapshot payload from current HP lists
                snapshot_data = {
                    'player_units': [u.to_dict(a_hp[i]) for i, u in enumerate(team_a)],
                    'opponent_units': [u.to_dict(b_hp[i]) for i, u in enumerate(team_b)],
                    'timestamp': time
                }
                try:
                    seq_expected = self._event_seq + 1
                    player_hp_list = [(u.id, u.name, a_hp[i]) for i, u in enumerate(team_a)]
                    opponent_hp_list = [(u.id, u.name, b_hp[i]) for i, u in enumerate(team_b)]
                    logger.info(f"[COMBAT] Emitting state_snapshot seq={seq_expected}, ts={time:.9f}, player_hp={player_hp_list}, opponent_hp={opponent_hp_list}")
                    # Also print to stdout for test harness visibility
                except Exception:
                    logger.info(f"[COMBAT] Emitting state_snapshot ts={time:.9f}")

                # Debug: show effects on specific failing unit 'laylo' at snapshot time
                try:
                    for u in team_a + team_b:
                        if getattr(u, 'id', None) == 'laylo':
                            try:
                                print(f"[SNAPSHOT DEBUG] time={time} laylo.effects={getattr(u, 'effects', None)}")
                            except Exception:
                                pass
                except Exception:
                    pass

                event_callback('state_snapshot', snapshot_data)

        # Timeout - winner by total HP
        sum_a = sum(max(0, h) for h in a_hp)
        sum_b = sum(max(0, h) for h in b_hp)
        winner = "team_a" if sum_a >= sum_b else "team_b"

        logger.info(f"[COMBAT] Timeout at {time:.2f}s, winner by HP: {winner}, sum_a={sum_a}, sum_b={sum_b}")
        result = self._finish_combat(winner, time, a_hp, b_hp, log, team_a if winner == "team_a" else team_b)
        result['timeout'] = True
        return result
        """Calculate damage from attacker to defender."""
        # Calculate damage: LoL-style armor reduction
        damage = attacker.attack * 100.0 / (100.0 + defender.defense)
        # Apply target damage reduction if present
        dr = getattr(defender, 'damage_reduction', 0.0)
        if dr:
            damage = damage * (1.0 - dr / 100.0)
        return max(1, int(damage))

    def _finish_combat(self, winner: str, time: float, a_hp: List[int], b_hp: List[int], log: List[str], winning_team: List['CombatUnit']) -> Dict[str, Any]:
        """Helper to create result dict"""
        # Calculate star sum of surviving units from winning team
        surviving_star_sum = 0
        for i, unit in enumerate(winning_team):
            if (winning_team == self.team_a and a_hp[i] > 0) or (winning_team == self.team_b and b_hp[i] > 0):
                surviving_star_sum += getattr(unit, 'star_level', 1)
        
        return {
            'winner': winner,
            'duration': time,
            'team_a_survivors': sum(1 for h in a_hp if h > 0),
            'team_b_survivors': sum(1 for h in b_hp if h > 0),
            'surviving_star_sum': surviving_star_sum,
            'log': log
        }

    def _process_team_attacks(
        self,
        attacking_team: List['CombatUnit'],
        defending_team: List['CombatUnit'],
        attacking_hp: List[int],
        defending_hp: List[int],
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ) -> Optional[str]:
        """Process attacks for one team. Returns winner if defending team is defeated, None otherwise."""
        for i, unit in enumerate(attacking_team):
            if attacking_hp[i] <= 0:
                continue

            # Attack if enough time has passed since last attack
            attack_interval = 1.0 / unit.attack_speed if unit.attack_speed > 0 else float('inf')
            if time - unit.last_attack_time >= attack_interval:
                target_idx = self._select_target(attacking_team, defending_team, attacking_hp, defending_hp, i)
                if target_idx is None:
                    # Attacking team wins
                    return "team_a" if side == "team_a" else "team_b"

                # Calculate damage
                damage = self._calculate_damage(unit, defending_team[target_idx])
                # Account for shield on the defender (if any) before applying HP loss
                defender = defending_team[target_idx]
                shield_absorbed = 0
                if getattr(defender, 'shield', 0) > 0 and damage > 0:
                    shield_absorbed = min(defender.shield, damage)
                    defender.shield = max(0, defender.shield - shield_absorbed)
                remaining_damage = max(0, damage - shield_absorbed)
                try:
                    old_hp = int(defending_hp[target_idx])
                except Exception:
                    old_hp = defending_hp[target_idx]

                # Use canonical emit_damage to mutate target HP and emit authoritative attack event
                try:
                    from .event_canonicalizer import emit_damage
                    payload = emit_damage(
                        event_callback=event_callback,
                        attacker=unit,
                        target=defender,
                        raw_damage=remaining_damage,
                        shield_absorbed=shield_absorbed,
                        damage_type='physical',
                        side=side,
                        timestamp=time,
                        cause='attack',
                    )
                except Exception:
                    payload = None

                # Synchronize local defending_hp mirror with authoritative unit hp
                try:
                    new_hp = int(getattr(defender, 'hp', defending_hp[target_idx]))
                except Exception:
                    new_hp = defending_hp[target_idx]
                defending_hp[target_idx] = max(0, new_hp)

                # Authoritative HP write debug (include expected seq for diagnostics)
                try:
                    seq_expected = self._event_seq + 1
                except Exception:
                    seq_expected = None

                # Log HP mutation for debugging ordering issues (include expected seq)
                try:
                    logger.info(f"[COMBAT HP MUTATION] seq={seq_expected} ts={time:.9f} side={side} target={defending_team[target_idx].id}:{defending_team[target_idx].name} hp={defending_hp[target_idx]}")
                    if defending_team[target_idx].id == 'olsak_10' or defending_team[target_idx].name.lower().startswith('olsak'):
                        print(f"[COMBAT HP MUTATION] seq={seq_expected} ts={time:.9f} target={defending_team[target_idx].id}:{defending_team[target_idx].name} hp={defending_hp[target_idx]}")
                except Exception:
                    pass

                # Log
                msg = f"[{time:.2f}s] {side.upper()[0]}:{unit.name} hits {'A' if side == 'team_b' else 'B'}:{defending_team[target_idx].name} for {damage}, hp={defending_hp[target_idx]}"
                log.append(msg)

                # Check if target died
                if defending_hp[target_idx] <= 0:
                    try:
                        print(f"[ATTACK DEBUG] attacker={getattr(unit,'id',None)} attacking_team_ids={[getattr(u,'id',None) for u in attacking_team]}")
                    except Exception:
                        pass
                    self._process_unit_death(
                        unit, defending_team, defending_hp, attacking_team, attacking_hp, target_idx, time, log, event_callback, side
                    )
                    # Ensure on_enemy_death effects emit stat_buff via canonical emitter
                    try:
                        for eff in getattr(unit, 'effects', []):
                            if eff.get('type') == 'on_enemy_death':
                                stats = eff.get('stats', []) or []
                                val = eff.get('value', 0)
                                for st in stats:
                                    try:
                                        emit_stat_buff(event_callback, unit, st, val, value_type='flat', duration=None, permanent=False, source=None, side=side, timestamp=time, cause='on_enemy_death')
                                    except Exception:
                                        pass
                    except Exception:
                        pass

                # Post-attack effect processing (lifesteal, mana on attack)
                # Lifesteal: heal attacker by damage * lifesteal%
                ls = getattr(unit, 'lifesteal', 0.0)
                if ls and damage > 0:
                    heal = int(damage * (ls / 100.0))
                    if heal > 0:
                        old_hp = attacking_hp[i]
                        attacking_hp[i] = min(unit.max_hp, attacking_hp[i] + heal)
                        log.append(f"{unit.name} lifesteals {heal}")
                        if event_callback:
                            from .event_canonicalizer import emit_unit_heal
                            emit_unit_heal(event_callback, unit, unit, heal, side=side, timestamp=time, current_hp=old_hp)

                # Mana gain: per attack
                unit.mana = min(unit.max_mana, unit.mana + unit.stats.mana_on_attack)

                # Send mana update event (canonicalized)
                if event_callback:
                    emit_mana_update(event_callback, unit, current_mana=unit.mana, max_mana=unit.max_mana, side=side, timestamp=time)

                # Check for skill casting if mana is full (reaches max_mana)
                skill_was_cast = False
                target_was_alive_before_skill = defending_hp[target_idx] > 0
                if hasattr(unit, 'skill') and unit.skill and unit.mana >= unit.max_mana:
                    skill_was_cast = True
                    self._process_skill_cast(unit, defending_team[target_idx], defending_hp, target_idx, time, log, event_callback, side)

                # Death callback and on-death effect triggers
                # Only process death if target died from skill (attack death was already processed above)
                if defending_hp[target_idx] <= 0 and skill_was_cast and target_was_alive_before_skill:
                    self._process_unit_death(unit, defending_team, defending_hp, attacking_team, attacking_hp, target_idx, time, log, event_callback, side)
                elif defending_hp[target_idx] > 0:
                    # Target is still alive -> check for on_ally_hp_below triggers on defending team
                    self._process_ally_hp_below_triggers(defending_team, defending_hp, target_idx, time, log, event_callback, side)

                # Update last attack time
                unit.last_attack_time = time

        return None

    def _process_skill_cast(
        self,
        caster: 'CombatUnit',
        target: 'CombatUnit',
        target_hp_list: List[int],
        target_idx: int,
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ):
        """Process skill casting for a unit."""
        from waffen_tactics.services.skill_executor import skill_executor
        from waffen_tactics.models.skill import SkillExecutionContext

        skill_data = caster.skill
        if not skill_data:
            return

        # Check if unit has new skill system
        new_skill = skill_data.get('effect', {}).get('skill')
        if new_skill:
            # Use new skill system
            context = SkillExecutionContext(
                caster=caster,
                team_a=self.team_a if hasattr(self, 'team_a') else [],
                team_b=self.team_b if hasattr(self, 'team_b') else [],
                combat_time=time,
                event_callback=event_callback,
            )

            try:
                import asyncio
                events = skill_executor.execute_skill(new_skill, context)

                # Minimal reliable forwarding: deliver every event returned by
                # the skill executor to the provided callback. Keep it simple
                # for tests that call _process_skill_cast directly.
                if event_callback:
                    for event_type, event_data in events:
                        try:
                            payload = dict(event_data) if isinstance(event_data, dict) else {'raw': event_data}
                        except Exception:
                            payload = {'raw': event_data}
                        if 'side' not in payload:
                            payload['side'] = side
                        if 'timestamp' not in payload:
                            payload['timestamp'] = getattr(context, 'combat_time', time)
                        try:
                            event_callback(event_type, payload)
                        except Exception:
                            pass
                    # try:
                    #     print(f"END ITER: {event_type}")
                    # except Exception:
                    #     pass

    

                # Add log messages for skill effects (use per-event timestamp if available)
                # Previously there was a fallback re-emission loop here that
                # sometimes duplicated events already forwarded above. The
                # primary forwarding loop reliably delivers all events returned
                # by the skill executor, so the fallback is unnecessary and
                # causes duplicate stat/buff events during replay. Skipping it
                # prevents double-emission and keeps emitted events deterministic.

                for event_type, event_data in events:
                    # Skip invalid payloads
                    if not isinstance(event_data, dict):
                        continue
                    evt_ts = event_data.get('timestamp', context.combat_time)
                    if event_type == 'unit_attack':
                        attacker = next((u for u in self.team_a + self.team_b if u.id == event_data.get('attacker_id')), None)
                        target = next((u for u in self.team_a + self.team_b if u.id == event_data.get('target_id')), None)
                        if attacker and target:
                            log.append(f"[{evt_ts:.2f}s] {attacker.name} deals {event_data['damage']} damage to {target.name}")
                    elif event_type == 'unit_heal':
                        healer = next((u for u in self.team_a + self.team_b if u.id == event_data.get('healer_id')), None)
                        target = next((u for u in self.team_a + self.team_b if u.id == event_data.get('unit_id')), None)
                        if healer and target:
                            log.append(f"[{evt_ts:.2f}s] {healer.name} heals {target.name} for {event_data['amount']} HP")
                    elif event_type == 'stat_buff':
                        caster = next((u for u in self.team_a + self.team_b if u.id == event_data.get('caster_id')), None)
                        target = next((u for u in self.team_a + self.team_b if u.id == event_data.get('unit_id')), None)
                        if caster and target:
                            buff_type = event_data.get('buff_type', 'buff')
                            stat = event_data['stat']
                            value = event_data['value']
                            duration = event_data['duration']
                            log.append(f"[{evt_ts:.2f}s] {caster.name} {buff_type}s {target.name}'s {stat} by {value} for {duration}s")
                    elif event_type == 'shield_applied':
                        caster = next((u for u in self.team_a + self.team_b if u.id == event_data.get('caster_id')), None)
                        target = next((u for u in self.team_a + self.team_b if u.id == event_data.get('unit_id')), None)
                        if caster and target:
                            amount = event_data['amount']
                            duration = event_data['duration']
                            log.append(f"[{evt_ts:.2f}s] {caster.name} grants {target.name} {amount} shield for {duration}s")
                    elif event_type == 'unit_stunned':
                        caster = next((u for u in self.team_a + self.team_b if u.id == event_data.get('caster_id')), None)
                        target = next((u for u in self.team_a + self.team_b if u.id == event_data.get('unit_id')), None)
                        if caster and target:
                            duration = event_data['duration']
                            log.append(f"[{evt_ts:.2f}s] {caster.name} stuns {target.name} for {duration}s")

                log.append(f"[{time:.2f}s] {caster.name} casts {new_skill.name}!")

                # CRITICAL: Sync HP lists from unit.hp after skill execution
                # Canonical emitters (emit_damage, emit_unit_heal) mutate unit.hp directly.
                # We must sync attacking_hp and defending_hp to match, otherwise final HP
                # sync at end of run_combat_simulation will overwrite correct values.
                for i, u in enumerate(attacking_team):
                    new_hp = max(0, int(getattr(u, 'hp', attacking_hp[i])))
                    if new_hp != attacking_hp[i]:
                        print(f"[HP SYNC] {u.id} attacking_hp[{i}]: {attacking_hp[i]} -> {new_hp}")
                    attacking_hp[i] = new_hp
                for i, u in enumerate(defending_team):
                    new_hp = max(0, int(getattr(u, 'hp', defending_hp[i])))
                    if new_hp != defending_hp[i]:
                        print(f"[HP SYNC] {u.id} defending_hp[{i}]: {defending_hp[i]} -> {new_hp}")
                    defending_hp[i] = new_hp

            except Exception as e:
                log.append(f"[{time:.2f}s] Skill execution failed: {e}")

        else:
            # Fallback to old skill system
            caster.mana = 0  # Reset mana to 0 after casting
            log.append(f"[{time:.2f}s] {caster.name} casts {skill_data['name']}!")

            # Send mana update event after reset (canonicalized)
            if event_callback:
                emit_mana_update(event_callback, caster, current_mana=caster.mana, max_mana=caster.max_mana, side=side, timestamp=time)

            # Apply skill effect (basic implementation)
            effect = skill_data.get('effect') or skill_data.get('effects')

            # Determine deterministic vs random selection for skill targets
            import os
            DETERMINISTIC_TARGETING = os.getenv('WAFFEN_DETERMINISTIC_TARGETING', '0') in ('1', 'true', 'True')

            # Normalize effects to a list so a skill can contain multiple sequential effects
            effects_list = []
            if isinstance(effect, list):
                effects_list = effect
            elif isinstance(effect, dict):
                effects_list = [effect]

            # Keep track of "last chosen" to allow effects to target the same unit
            last_chosen_idx = None

            # Helper to resolve candidate indices and pick one according to rules
            def choose_target_idx(target_spec: str, candidates_indices: list):
                if not candidates_indices:
                    return None
                if DETERMINISTIC_TARGETING:
                    return candidates_indices[0]
                import random as _rand
                return _rand.choice(candidates_indices)

            # If team lists are available, build defending_team reference to inspect positions
            have_teams = hasattr(self, 'team_a') and hasattr(self, 'team_b')
            defending_team_full = None
            if have_teams:
                defending_team_full = self.team_b if side == 'team_a' else self.team_a

            # Track damage/heal applied per index for summary
            damage_by_idx = {}

            for eff in effects_list:
                typ = eff.get('type')

                # Determine target selection rules for this effect
                target_spec = eff.get('target')  # e.g. 'attack_target','self','random_enemy','enemy_backline','enemy_frontline','same'

                # Build candidate indices on the provided target_hp_list (indexes correspond to defending side order)
                candidates = [i for i, hp in enumerate(target_hp_list) if hp > 0]

                # Filter by position if requested and we have defending team info
                if target_spec in ('enemy_backline', 'enemy_frontline') and defending_team_full is not None:
                    line = 'back' if target_spec == 'enemy_backline' else 'front'
                    candidates = [i for i in candidates if getattr(defending_team_full[i], 'position', 'front') == line]

                # Support explicit 'attack_target' (use given target_idx), 'self', 'same' (previous chosen)
                chosen_idx = None
                if target_spec == 'attack_target':
                    chosen_idx = target_idx
                elif target_spec == 'self':
                    chosen_idx = None  # will treat as applying to caster/self
                elif target_spec == 'same':
                    chosen_idx = last_chosen_idx
                elif target_spec == 'ally_random' and eff.get('ally_scope'):
                    # not implemented: fallback
                    chosen_idx = None
                else:
                    # random_enemy, enemy_frontline, enemy_backline, or None => pick from candidates
                    chosen_idx = choose_target_idx(target_spec or 'random_enemy', candidates)

                # Apply effect depending on type
                if typ == 'damage':
                    skill_damage = eff.get('amount', 0)
                    if skill_damage <= 0:
                        continue  # Skip negative or zero damage
                    # If chosen_idx is None -> apply to provided target (or caster in case of self)
                    apply_idx = chosen_idx if chosen_idx is not None else target_idx
                    # Guard index
                    if apply_idx is None or apply_idx < 0 or apply_idx >= len(target_hp_list):
                        apply_idx = target_idx

                    old_hp = target_hp_list[apply_idx]
                    target_hp_list[apply_idx] = max(0, target_hp_list[apply_idx] - skill_damage)
                    new_hp = target_hp_list[apply_idx]

                    # Resolve unit object for events/log
                    if defending_team_full is not None and apply_idx < len(defending_team_full):
                        unit_obj = defending_team_full[apply_idx]
                    else:
                        unit_obj = target

                    log.append(f"[{time:.2f}s] {skill_data.get('name')} deals {skill_damage} damage to {unit_obj.name}")
                    if event_callback:
                        event_callback('unit_attack', {
                            'attacker_id': caster.id,
                            'attacker_name': caster.name,
                            'target_id': unit_obj.id,
                            'target_name': unit_obj.name,
                            'damage': skill_damage,
                            'damage_type': eff.get('damage_type', 'physical'),
                            'old_hp': old_hp,
                            'new_hp': new_hp,
                            'is_skill': True,
                            'side': side,
                            'timestamp': time
                        })

                    # record damage for summary
                    damage_by_idx[apply_idx] = damage_by_idx.get(apply_idx, 0) + skill_damage
                    last_chosen_idx = apply_idx

                elif typ == 'heal':
                    amount = eff.get('amount', 0)
                    # Heal target (apply to provided target if chosen_idx None)
                    apply_idx = chosen_idx if chosen_idx is not None else target_idx
                    if apply_idx is None or apply_idx < 0 or apply_idx >= len(target_hp_list):
                        apply_idx = target_idx
                    old_hp = target_hp_list[apply_idx]
                    # When healing, we don't know max_hp easily without team lists; emit event and update value
                    target_hp_list[apply_idx] = min(getattr(target, 'max_hp', old_hp + amount), target_hp_list[apply_idx] + amount)
                    if event_callback:
                        from .event_canonicalizer import emit_unit_heal
                        target_obj = (defending_team_full[apply_idx] if defending_team_full and apply_idx < len(defending_team_full) else target)
                        emit_unit_heal(event_callback, target_obj, caster, amount, side=side, timestamp=time, current_hp=old_hp)
                    last_chosen_idx = apply_idx

                elif typ in ('stun', 'unit_stunned'):
                    duration = eff.get('duration', 1.0)
                    apply_idx = chosen_idx if chosen_idx is not None else target_idx
                    if apply_idx is None or apply_idx < 0 or apply_idx >= len(target_hp_list):
                        apply_idx = target_idx
                    if defending_team_full is not None and apply_idx < len(defending_team_full):
                        unit_obj = defending_team_full[apply_idx]
                    else:
                        unit_obj = target
                    if event_callback:
                        from .event_canonicalizer import emit_unit_stunned
                        emit_unit_stunned(event_callback, unit_obj, duration=duration, source=caster, side=side, timestamp=time)
                    last_chosen_idx = apply_idx

                elif typ in ('stat_buff', 'buff'):
                    stat = eff.get('stat')
                    value = eff.get('value')
                    duration = eff.get('duration', 5)
                    apply_idx = chosen_idx if chosen_idx is not None else target_idx
                    if apply_idx is None or apply_idx < 0 or apply_idx >= len(target_hp_list):
                        apply_idx = target_idx
                    if defending_team_full is not None and apply_idx < len(defending_team_full):
                        unit_obj = defending_team_full[apply_idx]
                    else:
                        unit_obj = target
                    if event_callback:
                        emit_stat_buff(event_callback, unit_obj, stat, value, value_type='flat', duration=duration, permanent=False, source=caster, side=side, timestamp=time)
                    last_chosen_idx = apply_idx

                else:
                    # Unknown effect: emit generic skill event for now
                    if event_callback:
                        event_callback('skill_effect', {
                            'caster_id': caster.id,
                            'effect': eff,
                            'side': side,
                            'timestamp': time
                        })
                    # don't modify last_chosen_idx

            # Emit a summary skill_cast event for UI and downstream handlers
            if event_callback:
                # Primary target: prefer last_chosen_idx, else provided target_idx
                primary_idx = last_chosen_idx if last_chosen_idx is not None else target_idx
                primary_unit = None
                primary_target_id = None
                primary_target_name = None
                primary_target_hp = None
                primary_target_max_hp = None
                primary_damage = None

                if primary_idx is not None and defending_team_full is not None and primary_idx < len(defending_team_full):
                    primary_unit = defending_team_full[primary_idx]
                    primary_target_id = primary_unit.id
                    primary_target_name = primary_unit.name
                    primary_target_hp = target_hp_list[primary_idx]
                    primary_target_max_hp = getattr(primary_unit, 'max_hp', None)
                    primary_damage = damage_by_idx.get(primary_idx, 0)
                else:
                    # Fallback to provided target object
                    if target is not None:
                        primary_target_id = getattr(target, 'id', None)
                        primary_target_name = getattr(target, 'name', None)
                        primary_target_hp = target_hp_list[target_idx] if (target_idx is not None and 0 <= target_idx < len(target_hp_list)) else None
                        primary_target_max_hp = getattr(target, 'max_hp', None)
                        primary_damage = damage_by_idx.get(primary_idx, 0) if primary_idx is not None else None

                event_callback('skill_cast', {
                    'caster_id': caster.id,
                    'caster_name': caster.name,
                    'skill_name': skill_data.get('name'),
                    'target_id': primary_target_id,
                    'target_name': primary_target_name,
                    'damage': primary_damage,
                    'target_hp': primary_target_hp,
                    'target_max_hp': primary_target_max_hp,
                    'side': side,
                    'timestamp': time,
                    'message': f"{caster.name} casts {skill_data.get('name')}!"
                })

        # Check if target died from skill
        if target_hp_list[target_idx] <= 0:
            # Use _process_unit_death to handle trait effects properly
            self._process_unit_death(caster, [target], target_hp_list, [caster], [caster.max_hp], 0, time, log, event_callback, side)

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
        hp_list: List[int],
        time: float,
        log: List[str],
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
        side: str
    ):
        """Process damage over time effects for a single team."""
        # First, process DoT ticks only for alive units
        for i, unit in enumerate(team):
            # Skip dead units — DoT should not tick on already-dead units
            if hp_list[i] <= 0:
                continue

            if not hasattr(unit, 'effects') or not unit.effects:
                continue

            # Process each effect on the unit
            effects_to_remove = []
            for j, effect in enumerate(unit.effects):
                if effect.get('type') == 'damage_over_time':
                    # Check if it's time for the next tick
                    next_tick = effect.get('next_tick_time', 0)
                    if time >= next_tick:
                        # Apply damage
                        damage = effect.get('damage', 0)
                        damage_type = effect.get('damage_type', 'physical')

                        # Apply damage (can be reduced by shields, etc.)
                        actual_damage = damage  # TODO: Apply damage reduction logic

                        # Compute tick metadata before mutating effect counters
                        before_ticks = int(effect.get('ticks_remaining', 0))
                        total_ticks = int(effect.get('total_ticks', before_ticks))
                        tick_index = (total_ticks - before_ticks) + 1 if total_ticks and before_ticks is not None else None

                        # Apply damage via canonical helper which will emit an authoritative attack
                        from .event_canonicalizer import emit_damage_over_time_tick
                        try:
                            payload = emit_damage_over_time_tick(
                                event_callback=event_callback,
                                target=unit,
                                damage=actual_damage,
                                damage_type=damage_type,
                                side=side,
                                timestamp=time,
                                effect_id=effect.get('id'),
                                tick_index=tick_index,
                                total_ticks=total_ticks,
                            )
                        except Exception:
                            payload = None

                        # Synchronize local hp mirror with authoritative unit hp
                        # CRITICAL: unit.hp should ALWAYS be set by emit_damage_over_time_tick
                        # If this raises an exception, it means emit_damage failed to set unit.hp
                        try:
                            authoritative_hp = int(getattr(unit, 'hp'))
                            hp_list[i] = max(0, authoritative_hp)
                        except (AttributeError, TypeError, ValueError) as e:
                            # This should NEVER happen - if it does, it's a critical bug
                            import sys
                            print(f"[CRITICAL BUG] DoT tick failed to get authoritative HP for {unit.name}: {e}", file=sys.stderr)
                            print(f"  unit.hp = {getattr(unit, 'hp', 'MISSING')}", file=sys.stderr)
                            print(f"  actual_damage = {actual_damage}", file=sys.stderr)
                            print(f"  hp_list[{i}] = {hp_list[i]}", file=sys.stderr)
                            # DO NOT use fallback calculation - fail loudly to expose the bug
                            raise

                        log.append(f"{unit.name} takes {actual_damage} {damage_type} damage from DoT")

                        # Update effect counters
                        ticks_remaining = effect.get('ticks_remaining', 0) - 1
                        if ticks_remaining > 0:
                            # Schedule next tick
                            interval = effect.get('interval', 1.0)
                            effect['ticks_remaining'] = ticks_remaining
                            effect['next_tick_time'] = time + interval
                        else:
                            # Effect expires — emit deterministic expire event
                            effects_to_remove.append(j)
                            if event_callback:
                                try:
                                    payload = {
                                        'unit_id': getattr(unit, 'id', None),
                                        'unit_name': getattr(unit, 'name', None),
                                        'effect_id': effect.get('id'),
                                        'unit_hp': hp_list[i],
                                        'timestamp': time,
                                    }
                                    event_callback('damage_over_time_expired', payload)
                                except Exception:
                                    # best-effort emit — never fail the simulator
                                    pass

                        # If the DoT killed the unit, process death triggers
                        try:
                            if hp_list[i] <= 0:
                                # Determine opposing team and their HP lists
                                if side == 'team_a':
                                    attacking_team = getattr(self, 'team_b', [])
                                    attacking_hp = getattr(self, 'b_hp', None)
                                else:
                                    attacking_team = getattr(self, 'team_a', [])
                                    attacking_hp = getattr(self, 'a_hp', None)
                                # Call central death processor (killer unknown for DoT)
                                try:
                                    self._process_unit_death(None, team, hp_list, attacking_team, attacking_hp or [], i, time, log, event_callback, side)
                                except Exception:
                                    pass
                        except Exception:
                            pass

            # Remove expired DoT effects (in reverse order to maintain indices)
            for j in reversed(effects_to_remove):
                unit.effects.pop(j)

        # Then, expire stat buffs and other effects for all units (including dead ones)
        for i, unit in enumerate(team):
            if not hasattr(unit, 'effects') or not unit.effects:
                continue

            effects_to_remove = []
            for j, effect in enumerate(unit.effects):
                if effect.get('expires_at') and effect.get('expires_at') <= time and effect.get('type') != 'damage_over_time':
                    effects_to_remove.append(j)
                    if event_callback:
                        try:
                            payload = {
                                'unit_id': getattr(unit, 'id', None),
                                'unit_name': getattr(unit, 'name', None),
                                'effect_id': effect.get('id'),
                                'unit_hp': hp_list[i],
                                'timestamp': time,
                            }
                            event_callback('effect_expired', payload)
                        except Exception:
                            # best-effort emit — never fail the simulator
                            pass

            # Remove expired stat effects
            for j in reversed(effects_to_remove):
                unit.effects.pop(j)

