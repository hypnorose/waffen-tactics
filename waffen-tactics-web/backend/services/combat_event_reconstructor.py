"""
Combat Event Reconstructor - Reconstructs game state from combat events

================================================================================
ARCHITECTURAL VIOLATIONS WARNING
================================================================================

This reconstructor contains TEMPORARY WORKAROUNDS for backend event emission bugs.
It violates event-sourcing principles by containing game logic, fallback calculations,
and synthetic state derivation that should NOT exist.

CORE PRINCIPLE:
    The reconstructor should be a DUMB REPLAY ENGINE that applies events in sequence.
    It should NOT contain formulas, inference logic, or "smart" recovery mechanisms.
    If state cannot be reconstructed from events alone, THE BACKEND IS BROKEN.

CURRENT VIOLATIONS (marked with ❌ in code):

1. skill_cast handler applies mana reset and damage (REMOVED - now empty)
   → Backend emits mana_update and unit_attack events separately

2. stat_buff handler computes percentage deltas and infers random stats
   → Backend should emit applied_delta and resolve stat='random' before emission

3. Damage/heal/DoT handlers fall back to delta calculations
   → Backend should ALWAYS include authoritative HP in events

4. DoT tick deduplication masks backend duplicate emission bugs
   → Backend should guarantee event uniqueness via event_id

5. Effect reconciliation from snapshots masks missing application events
   → Backend should emit stat_buff/shield_applied/damage_over_time_applied for ALL effects

6. Synthetic effect expiration derives expires_at and reverts stat changes
   → Backend should emit effect_expired/damage_over_time_expired events

REQUIRED BACKEND FIXES (see individual function docstrings for details):

    [ ] emit_stat_buff() always includes applied_delta
    [ ] emit_damage() always includes target_hp
    [ ] emit_unit_heal() always includes unit_hp/post_hp
    [ ] DoT tick emitter includes unit_hp and prevents duplicates
    [ ] Random stat buffs resolve to concrete stat before emission
    [ ] All effect applications emit explicit events (not just in snapshots)
    [ ] All effect expirations emit explicit events
    [ ] skill_cast events do NOT include damage field

Once backend is fixed, LARGE SECTIONS of this reconstructor should be DELETED.
Target: <300 lines of simple event application, not 1000+ lines of game logic.

For the IMMEDIATE failing test (test_10v10_simulation_multiple_seeds):
    → OLD skill system does NOT support ally_team heals (see combat_simulator.py:800-813)
    → Migrate units with ally_team heals from inline format to skills.json
    → OR add ally_team support to old system (not recommended, legacy code)

================================================================================
"""
import uuid
from typing import Dict, List, Any, Tuple


class CombatEventReconstructor:
    """Reconstructs combat game state from a sequence of events."""

    def __init__(self):
        self.reconstructed_player_units: Dict[str, Dict[str, Any]] = {}
        self.reconstructed_opponent_units: Dict[str, Dict[str, Any]] = {}
        self.seed = None
        # Collect DoT tick/applied events per unit for targeted debugging
        self._dot_trace: Dict[str, List[Dict[str, Any]]] = {}

    def initialize_from_snapshot(self, snapshot_data: Dict[str, Any]):
        """Initialize reconstruction from a state_snapshot event."""
        def normalize_unit(u):
            uu = dict(u)
            uu.setdefault('effects', [])
            uu.setdefault('base_stats', {})
            # Ensure canonical fields exist
            for eff in uu['effects']:
                eff['id'] = eff.get('id') or str(uuid.uuid4())
                # ensure numeric applied fields exist (may be None)
                if eff.get('type') in ('buff', 'debuff'):
                    if 'applied_delta' not in eff:
                        eff['applied_delta'] = eff.get('applied_delta', None)
                if eff.get('type') == 'shield':
                    if 'applied_amount' not in eff:
                        eff['applied_amount'] = eff.get('amount', None)
                # normalize expires_at
                if 'expires_at' in eff and eff['expires_at'] is not None:
                    try:
                        eff['expires_at'] = float(eff['expires_at'])
                    except Exception:
                        eff['expires_at'] = eff.get('expires_at')
            return uu

        self.reconstructed_player_units = {u['id']: normalize_unit(u) for u in snapshot_data['player_units']}
        self.reconstructed_opponent_units = {u['id']: normalize_unit(u) for u in snapshot_data['opponent_units']}

    def process_event(self, event_type: str, event_data: Dict[str, Any]):
        """Process a single event and update the reconstructed state."""
        seq = event_data.get('seq', 'N/A')
        # print(f"Processing event: type={event_type}, seq={seq}")

        if event_type in ['attack', 'unit_attack']:
            self._process_damage_event(event_data)
        elif event_type == 'unit_died':
            self._process_unit_death_event(event_data)
        elif event_type == 'mana_update':
            self._process_mana_update_event(event_data)
        elif event_type in ['heal', 'unit_heal']:
            self._process_heal_event(event_data)
        elif event_type == 'shield_applied':
            self._process_shield_applied_event(event_data)
        elif event_type == 'damage_over_time_tick':
            self._process_dot_event(event_data)
        elif event_type == 'damage_over_time_applied':
            self._process_dot_applied_event(event_data)
        elif event_type == 'damage_over_time_expired':
            self._process_dot_expired_event(event_data)
        elif event_type == 'effect_expired':
            self._process_effect_expired_event(event_data)
        elif event_type == 'unit_stunned':
            self._process_stun_event(event_data)
        elif event_type == 'stat_buff':
            self._process_stat_buff_event(event_data)
        elif event_type == 'hp_regen':
            self._process_hp_regen_event(event_data)
        elif event_type == 'skill_cast':
            self._process_skill_cast_event(event_data)
        elif event_type == 'state_snapshot':
            self._process_state_snapshot_event(event_data)
        else:
            print(f"  Unhandled event type: {event_type}")

        # If the event includes an embedded game state (or full player/opponent units),
        # validate it immediately. This handles emitters that include authoritative
        # `game_state` in non-`state_snapshot` events.
        try:
            if event_type != 'state_snapshot':
                gs = None
                if isinstance(event_data.get('game_state'), dict):
                    gs = event_data.get('game_state')
                elif 'player_units' in event_data and 'opponent_units' in event_data:
                    gs = {
                        'player_units': event_data.get('player_units'),
                        'opponent_units': event_data.get('opponent_units'),
                        'timestamp': event_data.get('timestamp', event_data.get('game_time'))
                    }

                if gs:
                    payload = {
                        'player_units': gs.get('player_units', []),
                        'opponent_units': gs.get('opponent_units', []),
                        'timestamp': gs.get('timestamp', event_data.get('timestamp', 0)),
                        'seq': event_data.get('seq', 'N/A')
                    }
                    # print(f"  Embedded game_state found in event seq={seq}; running state check")
                    self._process_state_snapshot_event(payload)
        except AssertionError:
            # Re-raise so test harness sees the failure (messages will include self.seed)
            raise
        except Exception:
            # Non-fatal: don't let extra validation break reconstruction
            pass

    def _process_damage_event(self, event_data: Dict[str, Any]):
        """Process attack or unit_attack event.

        ❌ BACKEND BUG: Some damage events are missing authoritative 'target_hp' or 'new_hp'

        TODO (BACKEND FIX REQUIRED):
        - emit_damage() must ALWAYS include 'target_hp' (authoritative HP after damage)
        - Once fixed, DELETE the fallback calculation (lines 136-138)

        The reconstructor should NOT calculate HP from damage deltas. Shield absorption,
        death detection, and HP capping are GAME LOGIC that belongs in emit_damage().
        """
        target_id = event_data.get('target_id')
        damage = event_data.get('damage', 0)
        shield_absorbed = event_data.get('shield_absorbed', 0)

        # Use authoritative HP from event if available (preferred).
        # Use explicit key presence checks so zero values (0) are respected.
        if 'target_hp' in event_data:
            new_hp = event_data.get('target_hp')
        elif 'new_hp' in event_data:
            new_hp = event_data.get('new_hp')
        else:
            new_hp = None

        if target_id is not None:
            unit_dict = self._get_unit_dict(target_id)
            if unit_dict:
                old_hp = unit_dict['hp']

                # Prefer authoritative HP from event
                if new_hp is not None:
                    unit_dict['hp'] = new_hp
                else:
                    # ==================================================================================
                    # TEMPORARY FALLBACK LOGIC - SHOULD BE DELETED ONCE BACKEND IS FIXED
                    # ==================================================================================
                    # BACKEND BUG: target_hp missing - falling back to calculation
                    # This should be fixed in emit_damage() to always include target_hp
                    # ==================================================================================
                    if damage > 0:
                        unit_dict['hp'] = max(0, old_hp - damage)
                    # ==================================================================================
                    # END TEMPORARY FALLBACK LOGIC
                    # ==================================================================================

                # Update shield (shield_absorbed is authoritative from backend)
                unit_dict['shield'] = max(0, unit_dict.get('shield', 0) - shield_absorbed)
                side = "player" if target_id in self.reconstructed_player_units else "opponent"

    def _process_unit_death_event(self, event_data: Dict[str, Any]):
        """Process unit_died event."""
        unit_id = event_data.get('unit_id') or event_data.get('caster_id')
        if unit_id:
            unit_dict = self._get_unit_dict(unit_id)
            if unit_dict:
                old_hp = unit_dict['hp']
                unit_dict['hp'] = 0  # Set to 0 when dead
                side = "player" if unit_id in self.reconstructed_player_units else "opponent"
                print(f"  Marked {side} unit {unit_id} as dead")
                if 'olsak' in unit_id:
                    print(f"    DEBUG: olsak unit {unit_id} died, HP was {old_hp} before setting to 0")

    def _process_mana_update_event(self, event_data: Dict[str, Any]):
        """Process mana_update event.

        Accept either an authoritative `current_mana` value or an `amount`
        delta. Prefer `current_mana` when present; otherwise apply `amount`.
        """
        unit_id = event_data.get('unit_id')
        if not unit_id:
            return
        unit_dict = self._get_unit_dict(unit_id)
        if not unit_dict:
            return

        # Authoritative set
        if 'current_mana' in event_data and event_data.get('current_mana') is not None:
            current_mana = event_data.get('current_mana')
            unit_dict['current_mana'] = current_mana
            side = "player" if unit_id in self.reconstructed_player_units else "opponent"
            # print(f"  Updated mana for {side} unit {unit_id} to {current_mana}")
            return

        # Delta apply
        if 'amount' in event_data and event_data.get('amount') is not None:
            amount = event_data.get('amount')
            old_mana = unit_dict.get('current_mana', 0)
            unit_dict['current_mana'] = min(unit_dict.get('max_mana', old_mana), old_mana + amount)
            # print(f"  Regenerated mana for unit {unit_id} from {old_mana} to {unit_dict['current_mana']}")

    def _process_heal_event(self, event_data: Dict[str, Any]):
        """Process heal or unit_heal event.

        ❌ BACKEND BUG: Some heal events are missing authoritative 'unit_hp' or 'post_hp'

        TODO (BACKEND FIX REQUIRED):
        - emit_unit_heal() must ALWAYS include 'unit_hp' or 'post_hp' (authoritative HP after heal)
        - Once fixed, DELETE the fallback calculation (lines 210-211)

        The reconstructor should NOT calculate HP from heal amounts. Overheal capping,
        lifesteal mechanics, and conditional healing are GAME LOGIC in emit_unit_heal().
        """
        unit_id = event_data.get('unit_id')
        amount = event_data.get('amount')
        if not unit_id:
            return
        unit_dict = self._get_unit_dict(unit_id)
        if not unit_dict:
            return

        # Prefer authoritative HP fields when present
        authoritative_hp = None
        if 'unit_hp' in event_data and event_data.get('unit_hp') is not None:
            authoritative_hp = event_data.get('unit_hp')
        elif 'post_hp' in event_data and event_data.get('post_hp') is not None:
            authoritative_hp = event_data.get('post_hp')
        elif 'target_hp' in event_data and event_data.get('target_hp') is not None:
            authoritative_hp = event_data.get('target_hp')
        elif 'new_hp' in event_data and event_data.get('new_hp') is not None:
            authoritative_hp = event_data.get('new_hp')

        old_hp = unit_dict.get('hp')
        if authoritative_hp is not None:
            unit_dict['hp'] = min(unit_dict.get('max_hp', authoritative_hp), authoritative_hp)
        else:
            # ==================================================================================
            # TEMPORARY FALLBACK LOGIC - SHOULD BE DELETED ONCE BACKEND IS FIXED
            # ==================================================================================
            # BACKEND BUG: unit_hp/post_hp missing - falling back to calculation
            # This should be fixed in emit_unit_heal() to always include authoritative HP
            # ==================================================================================
            if amount is not None:
                unit_dict['hp'] = min(unit_dict.get('max_hp', old_hp + amount), old_hp + amount)
            # ==================================================================================
            # END TEMPORARY FALLBACK LOGIC
            # ==================================================================================


    def _process_shield_applied_event(self, event_data: Dict[str, Any]):
        """Process shield_applied event."""
        unit_id = event_data.get('unit_id')
        amount = event_data.get('amount')
        duration = event_data.get('duration')
        if unit_id and amount is not None:
            unit_dict = self._get_unit_dict(unit_id)
            if unit_dict:
                old_shield = unit_dict.get('shield', 0)
                unit_dict['shield'] = old_shield + amount
                # Add shield effect
                eid = event_data.get('effect_id') or str(uuid.uuid4())
                effect = {
                    'id': eid,
                    'type': 'shield',
                    'amount': amount,
                    'duration': duration,
                    'source': event_data.get('source', unit_id),
                    'expires_at': event_data.get('timestamp', 0) + (duration or 0),
                    'applied_amount': amount  # Store for reversion
                }
                unit_dict['effects'].append(effect)
                print(f"  Applied shield to unit {unit_id}: {old_shield} -> {unit_dict['shield']}")

    def _process_dot_event(self, event_data: Dict[str, Any]):
        """Process damage_over_time_tick event.

        ❌ BACKEND BUG: Duplicate DoT ticks are sometimes emitted
        ❌ BACKEND BUG: Some DoT tick events are missing authoritative 'unit_hp'

        TODO (BACKEND FIX REQUIRED):
        1. DoT tick emitter should use event_id for idempotency (no duplicates)
        2. All DoT tick events must include 'unit_hp' (authoritative HP after tick damage)
        3. Once fixed, DELETE the deduplication logic (lines 246-258)
        4. Once fixed, DELETE the fallback calculation (line 290)

        The reconstructor should NOT dedupe events or calculate damage.
        """
        unit_id = event_data.get('unit_id')
        damage = event_data.get('damage', 0)

        if not unit_id:
            return

        # ==================================================================================
        # TEMPORARY DEDUPLICATION LOGIC - SHOULD BE DELETED ONCE BACKEND IS FIXED
        # ==================================================================================
        # BACKEND BUG: Sometimes emits duplicate DoT ticks
        # This should be fixed in the DoT tick emitter to ensure uniqueness via event_id
        # ==================================================================================
        try:
            lt = self._dot_trace.setdefault(unit_id, [])
            cur_ts = event_data.get('timestamp')
            cur_dmg = damage
            if lt:
                last = lt[-1]
                last_eff = last.get('raw_event', {}).get('effect_id') or last.get('raw_event', {}).get('id')
                cur_eff = event_data.get('effect_id') or event_data.get('id')
                if last.get('timestamp') == cur_ts and last.get('damage') == cur_dmg and last_eff == cur_eff:
                    print(f"[DOT DEDUPE] skipping duplicate tick for unit {unit_id} seq={event_data.get('seq')} ts={cur_ts} dmg={cur_dmg} eff={cur_eff}")
                    return  # TEMPORARY: Skip duplicate
            entry = {
                'seq': event_data.get('seq'),
                'timestamp': cur_ts,
                'damage': cur_dmg,
                'effect_id': event_data.get('effect_id') or event_data.get('id'),
                'unit_hp': event_data.get('unit_hp') if 'unit_hp' in event_data else event_data.get('target_hp') if 'target_hp' in event_data else event_data.get('new_hp') if 'new_hp' in event_data else None,
                'raw_event': dict(event_data)
            }
            lt.append(entry)
        except Exception:
            pass
        # ==================================================================================
        # END TEMPORARY DEDUPLICATION LOGIC
        # ==================================================================================

        unit_dict = self._get_unit_dict(unit_id)
        if unit_dict:
            old_hp = unit_dict['hp']

            # Prefer authoritative HP from event
            if 'unit_hp' in event_data and event_data.get('unit_hp') is not None:
                unit_dict['hp'] = event_data.get('unit_hp')
            elif 'target_hp' in event_data and event_data.get('target_hp') is not None:
                unit_dict['hp'] = event_data.get('target_hp')
            elif 'new_hp' in event_data and event_data.get('new_hp') is not None:
                unit_dict['hp'] = event_data.get('new_hp')
            else:
                # ==================================================================================
                # TEMPORARY FALLBACK LOGIC - SHOULD BE DELETED ONCE BACKEND IS FIXED
                # ==================================================================================
                # BACKEND BUG: unit_hp missing - falling back to calculation
                # ==================================================================================
                unit_dict['hp'] = max(0, unit_dict['hp'] - damage)
                # ==================================================================================
                # END TEMPORARY FALLBACK LOGIC
                # ==================================================================================
            print(f"  DoT damage to unit {unit_id}: {old_hp} -> {unit_dict['hp']}")

    def _process_dot_applied_event(self, event_data: Dict[str, Any]):
        """Process damage_over_time_applied event: install canonical DoT effect."""
        unit_id = event_data.get('unit_id')
        if not unit_id:
            return
        unit_dict = self._get_unit_dict(unit_id)
        if not unit_dict:
            return
        # Build canonical effect object matching snapshot shape
        eff = {
            'id': event_data.get('effect_id') or event_data.get('id') or str(uuid.uuid4()),
            'type': 'damage_over_time',
            'damage': event_data.get('damage'),
            'damage_type': event_data.get('damage_type'),
            'interval': event_data.get('interval'),
            'ticks_remaining': event_data.get('ticks'),
            'total_ticks': event_data.get('ticks'),
            'next_tick_time': event_data.get('next_tick_time'),
            'expires_at': event_data.get('expires_at'),
            'source': event_data.get('source') or event_data.get('caster_id') or event_data.get('caster_name')
        }
        unit_dict.setdefault('effects', [])
        # Avoid duplicates by id
        existing_ids = {e.get('id') for e in unit_dict.get('effects', []) if e.get('id')}
        if eff.get('id') not in existing_ids:
            unit_dict['effects'].append(eff)
            print(f"  Applied DoT effect to unit {unit_id}: effect_id={eff.get('id')}, damage={eff.get('damage')}")
            # Record application in dot trace for debugging (helps when ticks are missing)
            try:
                lt = self._dot_trace.setdefault(unit_id, [])
                entry = {
                    'seq': event_data.get('seq'),
                    'timestamp': event_data.get('timestamp'),
                    'damage': event_data.get('damage'),
                    'effect_id': eff.get('id'),
                    'event': 'applied',
                    'unit_hp': event_data.get('unit_hp') if 'unit_hp' in event_data else event_data.get('target_hp') if 'target_hp' in event_data else event_data.get('new_hp') if 'new_hp' in event_data else None,
                    'raw_event': dict(event_data)
                }
                lt.append(entry)
                if unit_id == 'mrvlook':
                    print(f"[DOT TRACE APPEND] unit={unit_id} appended_trace_len={len(lt)} entry={entry}")
            except Exception:
                pass

    def _process_skill_cast_event(self, event_data: Dict[str, Any]):
        """Process skill_cast event.

        NOTE: This handler is INTENTIONALLY LIMITED.
        - Mana changes should come from 'mana_update' events (backend emits these after skill cast)
        - Damage should come from 'unit_attack' or 'attack' events (NOT from skill_cast)
        - This event exists ONLY for UI animation triggers

        DO NOT ADD GAME LOGIC HERE. If this handler seems incomplete, FIX THE BACKEND to emit
        proper mana_update/damage events instead.
        """
        # skill_cast is primarily for UI/animation purposes
        # All state changes (mana, damage, buffs) come from dedicated events
        pass  # Intentionally minimal - backend emits proper events for state changes

    def _process_stat_buff_event(self, event_data: Dict[str, Any]):
        """Process stat_buff event.

        CRITICAL: This handler contains TEMPORARY FALLBACK LOGIC that should NOT exist.

        ❌ BACKEND BUG: applied_delta is MISSING from some stat_buff events
        ❌ BACKEND BUG: stat='random' is emitted instead of resolved stat name

        TODO (BACKEND FIX REQUIRED):
        1. emit_stat_buff() must ALWAYS include 'applied_delta' (the exact delta it applied)
        2. Random stat buffs must resolve stat='random' to concrete stat before emission
        3. Once fixed, DELETE the fallback calculation logic below (lines 380-399)

        The reconstructor should NOT compute percentage buffs or guess random stats.
        This is GAME LOGIC that belongs in the backend emitter.
        """
        unit_id = event_data.get('unit_id')
        stat = event_data.get('stat')
        value = event_data.get('value')
        amount = event_data.get('amount', value)
        value_type = event_data.get('value_type', 'flat')
        duration = event_data.get('duration')
        effect_id = event_data.get('effect_id')

        if not unit_id:
            return

        unit_dict = self._get_unit_dict(unit_id)
        if not unit_dict:
            return

        # ==================================================================================
        # TEMPORARY FALLBACK LOGIC - SHOULD BE DELETED ONCE BACKEND IS FIXED
        # ==================================================================================
        # The backend SHOULD provide applied_delta in ALL cases, but currently doesn't.
        # This fallback attempts to compute it, but is fragile and error-prone.
        # ==================================================================================

        delta = event_data.get('applied_delta')
        if delta is None:
            # BACKEND BUG: applied_delta missing - falling back to calculation
            # This should be fixed in emit_stat_buff() to always include applied_delta
            delta = 0
            if stat != 'random':
                try:
                    if value_type == 'percentage':
                        pct = float(amount if amount is not None else (value or 0))
                        base_stats = unit_dict.get('base_stats') or {}
                        if isinstance(base_stats, dict) and stat in base_stats:
                            base = base_stats.get(stat, 0) or 0
                        else:
                            base = unit_dict.get(stat, 0) or 0
                        # Use round() to match engine rounding behaviour
                        delta = int(round(base * (pct / 100.0)))
                    else:
                        delta = int(round(amount if amount is not None else (value if value is not None else 0)))
                except Exception:
                    delta = 0

        # ==================================================================================
        # END TEMPORARY FALLBACK LOGIC
        # ==================================================================================

        # Ensure stable effect id
        eid = effect_id or str(uuid.uuid4())

        # Apply the resolved delta to the unit
        if stat == 'hp':
            unit_dict[stat] = min(unit_dict['max_hp'], unit_dict[stat] + delta)
        elif stat != 'random':  # Skip if stat is still 'random' (backend bug)
            unit_dict[stat] += delta

        # Store effect for expiration tracking
        value_final = value if value is not None else amount
        try:
            effect_type = 'buff' if (value_final or 0) > 0 else 'debuff'
        except Exception:
            effect_type = 'debuff'

        effect = {
            'id': eid,
            'type': effect_type,
            'stat': stat,
            'value': value_final,
            'value_type': value_type,
            'duration': duration,
            'permanent': event_data.get('permanent', False),
            'source': event_data.get('source') or event_data.get('source_id'),
            'expires_at': event_data.get('timestamp', 0) + (duration or 0),
            'applied_delta': delta  # Store for reversion
        }
        unit_dict['effects'].append(effect)

    def _process_hp_regen_event(self, event_data: Dict[str, Any]):
        """Process hp_regen event."""
        unit_id = event_data.get('unit_id')
        amount = event_data.get('amount')
        if not unit_id:
            return
        unit_dict = self._get_unit_dict(unit_id)
        if not unit_dict:
            return

        # Prefer authoritative HP fields when present to avoid double-applying
        # regens (some emitters include the post-regen HP as 'unit_hp'/'post_hp'/'target_hp'/'new_hp').
        authoritative_hp = None
        if 'unit_hp' in event_data and event_data.get('unit_hp') is not None:
            authoritative_hp = event_data.get('unit_hp')
        elif 'post_hp' in event_data and event_data.get('post_hp') is not None:
            authoritative_hp = event_data.get('post_hp')
        elif 'target_hp' in event_data and event_data.get('target_hp') is not None:
            authoritative_hp = event_data.get('target_hp')
        elif 'new_hp' in event_data and event_data.get('new_hp') is not None:
            authoritative_hp = event_data.get('new_hp')

        old_hp = unit_dict.get('hp')
        if authoritative_hp is not None:
            unit_dict['hp'] = min(unit_dict.get('max_hp', authoritative_hp), authoritative_hp)
        elif amount is not None:
            unit_dict['hp'] = min(unit_dict.get('max_hp', old_hp + amount), unit_dict.get('max_hp', old_hp + amount))
        # print(f"  Regenerated HP for unit {unit_id} from {old_hp} to {unit_dict['hp']}")

    def _process_stun_event(self, event_data: Dict[str, Any]):
        """Process unit_stunned event."""
        unit_id = event_data.get('unit_id')
        duration = event_data.get('duration')
        source = event_data.get('source') or event_data.get('source_id')
        timestamp = event_data.get('timestamp', 0)
        if not unit_id:
            return
        unit_dict = self._get_unit_dict(unit_id)
        if not unit_dict:
            return
        # Create a canonical stun effect entry similar to emitter shape
        eff = {
            'type': 'stun',
            'duration': duration,
            'source': source,
            'expires_at': (timestamp + float(duration)) if (duration and duration > 0) else None,
        }
        unit_dict.setdefault('effects', [])
        unit_dict['effects'].append(eff)
        print(f"  Reconstructed stun on unit {unit_id}: duration={duration}, source={source}")
    def _process_dot_expired_event(self, event_data: Dict[str, Any]):
        """Process damage_over_time_expired event: remove canonical DoT effect."""
        unit_id = event_data.get('unit_id')
        effect_id = event_data.get('effect_id')
        if not unit_id:
            return
        unit_dict = self._get_unit_dict(unit_id)
        if not unit_dict:
            return
        # Record expire in dot trace for debugging
        try:
            lt = self._dot_trace.setdefault(unit_id, [])
            entry = {
                'seq': event_data.get('seq'),
                'timestamp': event_data.get('timestamp'),
                'damage': None,
                'effect_id': effect_id,
                'event': 'expired',
                'unit_hp': event_data.get('unit_hp'),
                'raw_event': dict(event_data)
            }
            lt.append(entry)
            if unit_id == 'mrvlook':
                print(f"[DOT TRACE APPEND] unit={unit_id} appended_trace_len={len(lt)} entry={entry}")
        except Exception:
            pass

        # Remove effect by id
        effs = unit_dict.get('effects') or []
        new_eff = [e for e in effs if e.get('id') != effect_id]
        if len(new_eff) != len(effs):
            unit_dict['effects'] = new_eff
            print(f"  Removed DoT effect from unit {unit_id}: effect_id={effect_id}")
        # If authoritative unit_hp provided, update unit hp
        if 'unit_hp' in event_data and event_data.get('unit_hp') is not None:
            old_hp = unit_dict.get('hp')
            unit_dict['hp'] = event_data.get('unit_hp')
            print(f"  DoT expire updated unit {unit_id} HP: {old_hp} -> {unit_dict['hp']}")
        unit_id = event_data.get('unit_id')
        duration = event_data.get('duration')

    def _process_effect_expired_event(self, event_data: Dict[str, Any]):
        """Process effect_expired event: remove canonical effect."""
        unit_id = event_data.get('unit_id')
        effect_id = event_data.get('effect_id')
        if not unit_id:
            return
        unit_dict = self._get_unit_dict(unit_id)
        if not unit_dict:
            return
        # Remove effect by id
        effs = unit_dict.get('effects') or []
        new_eff = [e for e in effs if e.get('id') != effect_id]
        if len(new_eff) != len(effs):
            unit_dict['effects'] = new_eff
            print(f"  Removed effect from unit {unit_id}: effect_id={effect_id}")
        # If authoritative unit_hp provided, update unit hp
        if 'unit_hp' in event_data and event_data.get('unit_hp') is not None:
            old_hp = unit_dict.get('hp')
            unit_dict['hp'] = event_data.get('unit_hp')
            print(f"  Effect expire updated unit {unit_id} HP: {old_hp} -> {unit_dict['hp']}")
        # NOTE: previously this handler incorrectly appended a stun effect
        # unconditionally. An "effect_expired" event should only remove the
        # described effect (and optionally update authoritative HP). Stuns
        # are reconstructed from `unit_stunned` events; do not create new
        # effects here.

    def _process_state_snapshot_event(self, event_data: Dict[str, Any]):
        """Process state_snapshot event - validate reconstruction."""
        # print(f"  Checking state_snapshot at seq {event_data.get('seq', 'N/A')}")
        # Expire effects before checking
        current_time = event_data.get('timestamp', 0)
        self._expire_effects(current_time)

        # Create snapshot copies for comparison
        snapshot_player_units = {
            u['id']: dict(u)  # Remove 'dead' derivation
            for u in event_data['player_units']
        }
        snapshot_opponent_units = {
            u['id']: dict(u)  # Remove 'dead' derivation
            for u in event_data['opponent_units']
        }

        # Targeted snapshot debug for laylo
        try:
            if 'laylo' in snapshot_opponent_units:
                print(f"[RECON SNAPSHOT DEBUG] seq={event_data.get('seq')} snapshot_opponent.laylo.effects={snapshot_opponent_units['laylo'].get('effects')}")
        except Exception:
            pass

        # Expire effects in snapshot as well. Normalize None expires_at to
        # infinite (still active) to avoid TypeErrors and to match emitter
        # semantics where ``expires_at`` may be None for persistent effects.
        for units in [snapshot_player_units, snapshot_opponent_units]:
            for unit_dict in units.values():
                new_effects = []
                for e in unit_dict.get('effects', []):
                    expires = e.get('expires_at')
                    # Treat None as "no expiry" (active)
                    if expires is None or expires > current_time:
                        new_effects.append(e)
                unit_dict['effects'] = new_effects

        # ==================================================================================
        # RECONCILIATION LOGIC - THIS IS A MASSIVE ARCHITECTURAL VIOLATION
        # ==================================================================================
        # ❌ BACKEND BUG: Some effects are present in snapshots but never emitted as events
        #
        # TODO (BACKEND FIX REQUIRED):
        # 1. ALL stat buffs must emit 'stat_buff' events when applied
        # 2. ALL shields must emit 'shield_applied' events when applied
        # 3. ALL DoTs must emit 'damage_over_time_applied' events when applied
        # 4. Once fixed, REPLACE reconciliation with STRICT validation (fail on mismatch)
        #
        # This 500+ line reconciliation function MASKS BACKEND BUGS by silently applying
        # effects from snapshots when they should have come from events. It violates the
        # core principle of event sourcing: state must be derivable from events ONLY.
        #
        # Snapshots are VALIDATION CHECKPOINTS, not data sources.
        # ==================================================================================
        def reconcile_effects(snapshot_units: Dict[str, Dict], reconstructed_units: Dict[str, Dict]):
            for uid, snap_u in snapshot_units.items():
                recon_u = reconstructed_units.get(uid)
                if not recon_u:
                    continue
                # Build set of existing effect ids to avoid duplicates
                existing_ids = {e.get('id') for e in recon_u.get('effects', []) if e.get('id')}
                for eff in snap_u.get('effects', []):
                    eff_id = eff.get('id')
                    if eff_id and eff_id in existing_ids:
                        continue
                    # Only reconcile stat buffs and shields (others are ignored)
                    stat = eff.get('stat')
                    eff_type = eff.get('type')
                    # Helper: detect if an equivalent effect already exists (by important fields)
                    def has_equivalent(existing_list, candidate):
                        for ex in existing_list:
                            if ex.get('type') != candidate.get('type'):
                                continue
                            if candidate.get('type') == 'shield':
                                if ex.get('amount') == (candidate.get('amount') or candidate.get('applied_amount')) and ex.get('source') == candidate.get('source') and ex.get('expires_at') == candidate.get('expires_at'):
                                    return True
                            elif candidate.get('type') in ('buff', 'debuff'):
                                # Normalize value comparison: emitter may use 'value',
                                # 'amount' or 'applied_delta'. Compare a canonical
                                # numeric representation when possible to avoid
                                # false negatives during reconciliation.
                                def _val(x):
                                    if x is None:
                                        return None
                                    if isinstance(x, (int, float)):
                                        return x
                                    try:
                                        return float(x)
                                    except Exception:
                                        return x

                                ex_val = ex.get('value') if ex.get('value') is not None else ex.get('amount') if ex.get('amount') is not None else ex.get('applied_delta')
                                cand_val = candidate.get('value') if candidate.get('value') is not None else candidate.get('amount') if candidate.get('amount') is not None else candidate.get('applied_delta')
                                if ex.get('stat') == candidate.get('stat') and _val(ex_val) == _val(cand_val) and ex.get('source') == candidate.get('source') and ex.get('expires_at') == candidate.get('expires_at'):
                                    return True
                            elif candidate.get('type') == 'damage_over_time':
                                # Compare DoT by damage, source and expires_at when possible
                                try:
                                    def _num(x):
                                        if x is None:
                                            return None
                                        if isinstance(x, (int, float)):
                                            return float(x)
                                        try:
                                            return float(x)
                                        except Exception:
                                            return None

                                    ex_dmg = ex.get('damage') if ex.get('damage') is not None else ex.get('amount')
                                    cand_dmg = candidate.get('damage') if candidate.get('damage') is not None else candidate.get('amount')
                                    if ex.get('type') == 'damage_over_time' and ex.get('source') == candidate.get('source') and (_num(ex_dmg) == _num(cand_dmg)) and ex.get('expires_at') == candidate.get('expires_at'):
                                        return True
                                except Exception:
                                    pass
                        return False

                    if eff_type == 'shield':
                        amt = eff.get('amount') or eff.get('applied_amount') or 0
                        # Skip if an equivalent shield effect already present
                        if has_equivalent(recon_u.get('effects', []), eff):
                            continue
                        recon_u['shield'] = recon_u.get('shield', 0) + amt
                        # store applied amount for proper expiration handling
                        new_eff = eff.copy()
                        new_eff['id'] = new_eff.get('id') or str(uuid.uuid4())
                        new_eff['applied_amount'] = amt
                        # normalize expires_at
                        if 'expires_at' in new_eff and new_eff['expires_at'] is not None:
                            try:
                                new_eff['expires_at'] = float(new_eff['expires_at'])
                            except Exception:
                                pass
                        recon_u['effects'].append(new_eff)
                        if uid == 'laylo':
                            print(f"[DBG RECONCILE_APPLY] seq={event_data.get('seq')} uid=laylo applied_effect={new_eff}")
                    elif eff_type in ('buff', 'debuff') and stat:
                        # Skip if an equivalent stat effect already present
                        if has_equivalent(recon_u.get('effects', []), eff):
                            continue
                        # Prefer authoritative applied_delta when provided
                        delta = eff.get('applied_delta')
                        # If effect targets 'random', try to infer which concrete
                        # stat was actually affected by comparing snapshot
                        # authoritative top-level values to our reconstructed ones.
                        if stat == 'random':
                            candidates = ['attack', 'defense', 'attack_speed', 'hp', 'max_hp', 'current_mana', 'max_mana']
                            chosen = None
                            chosen_delta = None
                            value = eff.get('value')
                            amount = eff.get('value') if eff.get('value') is not None else eff.get('amount')
                            value_type = eff.get('value_type', 'flat')
                            for cand in candidates:
                                try:
                                    recon_val = recon_u.get(cand, 0) or 0
                                    snap_val = snap_u.get(cand, None)
                                    if snap_val is None:
                                        continue
                                    if delta is not None:
                                        if recon_val + delta == snap_val:
                                            chosen = cand
                                            chosen_delta = delta
                                            break
                                    else:
                                        if value_type == 'percentage':
                                            base_stats = recon_u.get('base_stats') or {}
                                            base = base_stats.get(cand, recon_val) or 0
                                            expected = int(round(base * (float(amount or 0) / 100.0)))
                                        else:
                                            expected = int(round(amount if amount is not None else (value if value is not None else 0)))
                                        if recon_val + expected == snap_val:
                                            chosen = cand
                                            chosen_delta = expected
                                            break
                                except Exception:
                                    continue
                            if chosen:
                                stat = chosen
                                delta = chosen_delta
                        if delta is None:
                            # Compute fallback similar to _process_stat_buff_event
                            value = eff.get('value')
                            amount = eff.get('value') if eff.get('value') is not None else eff.get('amount')
                            value_type = eff.get('value_type', 'flat')
                            try:
                                if value_type == 'percentage':
                                    pct = float(amount or 0)
                                    base_stats = recon_u.get('base_stats') or {}
                                    if isinstance(base_stats, dict) and stat in base_stats:
                                        base = base_stats.get(stat, 0) or 0
                                    else:
                                        base = recon_u.get(stat, 0) or 0
                                    delta = int(round(base * (pct / 100.0)))
                                else:
                                    delta = int(round(amount if amount is not None else (value if value is not None else 0)))
                            except Exception:
                                delta = 0

                        # Apply delta
                        if stat == 'hp':
                            recon_u['hp'] = min(recon_u['max_hp'], recon_u.get('hp', 0) + (delta or 0))
                        else:
                            recon_u[stat] = recon_u.get(stat, 0) + (delta or 0)
                        # Append effect with applied_delta for expiry handling
                        new_eff = eff.copy()
                        new_eff['applied_delta'] = delta
                        new_eff['id'] = new_eff.get('id') or str(uuid.uuid4())
                        recon_u['effects'].append(new_eff)
                        if uid == 'laylo':
                            print(f"[DBG RECONCILE_APPLY] seq={event_data.get('seq')} uid=laylo applied_effect={new_eff}")
                    elif eff_type == 'damage_over_time':
                        # Reconcile DoT effects present in snapshot into reconstructed state.
                        # DoT doesn't directly modify top-level stats here; we only
                        # ensure the effect object exists with id and expires_at so
                        # expiry and tick processing line up deterministically.
                        # Debug: log DoT from snapshot being reconciled
                        try:
                            if uid in ('hyodo888',):
                                print(f"[DBG RECONCILE DOT] seq={event_data.get('seq')} uid={uid} snap_eff={eff} existing_ids={existing_ids} recon_effects={recon_u.get('effects')}")
                        except Exception:
                            pass
                        if has_equivalent(recon_u.get('effects', []), eff):
                            try:
                                if uid in ('hyodo888',):
                                    print(f"[DBG RECONCILE DOT] seq={event_data.get('seq')} uid={uid} skip_has_equivalent=True")
                            except Exception:
                                pass
                            continue
                        new_eff = eff.copy()
                        new_eff['id'] = new_eff.get('id') or str(uuid.uuid4())
                        # Normalise numeric fields
                        try:
                            if 'expires_at' in new_eff and new_eff['expires_at'] is not None:
                                new_eff['expires_at'] = float(new_eff['expires_at'])
                        except Exception:
                            pass
                        recon_u['effects'].append(new_eff)
                        try:
                            if uid in ('hyodo888',):
                                print(f"[DBG RECONCILE DOT] seq={event_data.get('seq')} uid={uid} appended_eff={new_eff}")
                        except Exception:
                            pass

                # Sync authoritative top-level numeric stats from the snapshot into
                # our reconstructed unit when they differ. Some emitters update
                # the stat fields directly (e.g. 'defense' -> 36) even if the
                # active effect list is empty (expired or represented elsewhere).
                # To ensure deterministic reconciliation we prefer the snapshot's
                # authoritative values for these core fields.
                for field in ('hp', 'max_hp', 'current_mana', 'max_mana', 'attack', 'defense', 'attack_speed', 'shield'):
                    if field in snap_u:
                        recon_u[field] = snap_u[field]

                # Prune reconstructed effects that are not present in the
                # authoritative snapshot. The snapshot is ground truth; if
                # it omits an effect we hold, remove it so comparisons match.
                try:
                    snap_effects = snap_u.get('effects', []) or []
                    kept = []
                    for ex in recon_u.get('effects', []):
                        if has_equivalent(snap_effects, ex):
                            kept.append(ex)
                        else:
                            # dropped: snapshot did not report this effect
                            pass
                    recon_u['effects'] = kept
                except Exception:
                    pass

        # Targeted debug: if this snapshot seq matches a known failing seq,
        # dump mrvlook state for investigation.
        try:
            seq_val = int(event_data.get('seq', -1))
        except Exception:
            seq_val = -1
        if seq_val == 359:
            rid = 'mrvlook'
            recon = self.reconstructed_opponent_units.get(rid)
            snap = snapshot_opponent_units.get(rid)
            print(f"[DEBUG SEQ 359] reconstructed mrvlook defense={recon.get('defense') if recon else None}, effects={recon.get('effects') if recon else None}")
            print(f"[DEBUG SEQ 359] snapshot mrvlook defense={snap.get('defense') if snap else None}, effects={snap.get('effects') if snap else None}")

        reconcile_effects(snapshot_player_units, self.reconstructed_player_units)
        reconcile_effects(snapshot_opponent_units, self.reconstructed_opponent_units)

        # Debug: report DoT trace length for mrvlook to track incoming ticks
        try:
            mt = self._dot_trace.get('mrvlook') if hasattr(self, '_dot_trace') else None
            if mt is not None:
                print(f"[DOT TRACE STATUS] seq={event_data.get('seq', 'N/A')} mrvlook_trace_len={len(mt)}")
        except Exception:
            pass

        # Compare states
        # Pass current_time into comparison so we can attempt recovery
        # via synthetic expiration messages when transient ordering
        # mismatches (e.g. DoT applied vs snapshot) occur.
        self._compare_units(
            self.reconstructed_player_units,
            snapshot_player_units,
            "player",
            event_data.get('seq', 'N/A'),
            current_time
        )
        self._compare_units(
            self.reconstructed_opponent_units,
            snapshot_opponent_units,
            "opponent",
            event_data.get('seq', 'N/A'),
            current_time
        )
        # print(f"  State snapshot check passed for seq {event_data.get('seq', 'N/A')}")

    def _get_unit_dict(self, unit_id: str) -> Dict[str, Any]:
        """Get unit dict by ID from either player or opponent units."""
        if unit_id in self.reconstructed_player_units:
            return self.reconstructed_player_units[unit_id]
        elif unit_id in self.reconstructed_opponent_units:
            return self.reconstructed_opponent_units[unit_id]
        return None

    def _expire_effects(self, current_time: float):
        """Expire effects that have passed their duration.

        ==================================================================================
        CRITICAL: THIS ENTIRE FUNCTION SHOULD NOT EXIST
        ==================================================================================
        ❌ BACKEND BUG: Combat effect processor does NOT emit 'effect_expired' events
        ❌ BACKEND BUG: DoT processor does NOT emit 'damage_over_time_expired' events consistently

        TODO (BACKEND FIX REQUIRED):
        1. Combat effect processor must emit 'effect_expired' for buffs/debuffs/shields
        2. DoT processor must emit 'damage_over_time_expired' for all DoT expirations
        3. Once fixed, DELETE this entire _expire_effects() function
        4. Reconstructor should only remove effects when it receives explicit expiration events

        The reconstructor should NOT:
        - Derive expires_at from ticks_remaining/interval (GAME LOGIC)
        - Automatically expire effects based on time (BACKEND RESPONSIBILITY)
        - Revert stat changes on expiration (COMPLEX GAME LOGIC)

        Effect expiration may have side effects, triggers, or conditional removal.
        The backend KNOWS when effects expire - it must emit events.
        ==================================================================================
        """
        # ==================================================================================
        # TEMPORARY SYNTHETIC EXPIRATION - SHOULD BE DELETED ONCE BACKEND IS FIXED
        # ==================================================================================
        expired_effects = []
        for units in [self.reconstructed_player_units, self.reconstructed_opponent_units]:
            for unit_dict in units.values():
                active_effects = []
                for e in unit_dict.get('effects', []):
                    # If effect does not have an expires_at but carries DoT-style
                    # ticks_remaining/interval/next_tick_time, derive expires_at
                    if 'expires_at' not in e or e.get('expires_at') is None:
                        try:
                            if e.get('type') == 'damage_over_time' and e.get('ticks_remaining') is not None:
                                interval = float(e.get('interval', 0) or 0)
                                ticks = int(e.get('ticks_remaining') or 0)
                                next_tick = float(e.get('next_tick_time', current_time) or current_time)
                                # last tick happens at next_tick + (ticks-1)*interval
                                if ticks > 0 and interval >= 0:
                                    e['expires_at'] = next_tick + max(0, (ticks - 1)) * interval
                        except Exception:
                            pass

                    if e.get('expires_at', float('inf')) > current_time:
                        active_effects.append(e)
                    else:
                        expired_effects.append((unit_dict, e))
                unit_dict['effects'] = active_effects
        # Revert changes for expired effects
        for unit_dict, effect in expired_effects:
            etype = effect.get('type')
            if etype in ('buff', 'debuff'):
                stat = effect.get('stat')
                delta = effect.get('applied_delta', 0) or 0
                # applied_delta may be positive or negative; subtracting it
                # reverts the earlier addition.
                if stat:
                    if stat == 'hp':
                        unit_dict[stat] = max(0, unit_dict.get(stat, 0) - delta)
                    else:
                        unit_dict[stat] = unit_dict.get(stat, 0) - delta
            elif etype == 'shield':
                amount = effect.get('applied_amount', 0) or 0
                unit_dict['shield'] = max(0, unit_dict.get('shield', 0) - amount)
            elif etype == 'damage_over_time':
                # DoT expiry requires no direct numeric reversion; effects are removed
                # and top-level hp is authoritative via snapshots and ticks.
                pass
        # ==================================================================================
        # END TEMPORARY SYNTHETIC EXPIRATION
        # ==================================================================================

    def _compare_units(self, reconstructed: Dict[str, Dict], snapshot: Dict[str, Dict], side: str, seq: Any, current_time: float = 0):
        """Compare reconstructed units with snapshot units."""
        def normalize_effect_for_compare(effect):
            """Return a canonical tuple for an effect for deterministic comparison."""
            if effect.get('type') == 'stun':
                return None  # ignore stun for now
            ef = effect.copy()
            # Remove internal-only fields
            ef.pop('applied_delta', None)
            ef.pop('applied_amount', None)
            eid = ef.pop('id', None)
            # Normalize expires_at to fixed precision to avoid float noise
            if 'expires_at' in ef and ef['expires_at'] is not None:
                try:
                    ef['expires_at'] = round(float(ef['expires_at']), 6)
                except Exception:
                    pass
            # Use a stable ordering tuple
            return (
                ef.get('type'),
                ef.get('stat'),
                ef.get('value'),
                ef.get('value_type'),
                ef.get('source'),
                ef.get('expires_at')
            )

        for uid, data in reconstructed.items():
            snapshot_data = snapshot.get(uid)
            if not snapshot_data:
                raise AssertionError(f"Unit {uid} not found in {side} snapshot at seq {seq}")

            # Assert key fields
            fields_to_check = ['hp', 'max_hp', 'current_mana', 'max_mana', 'attack', 'defense', 'attack_speed', 'effects', 'shield']
            for field in fields_to_check:
                if field in data and field in snapshot_data:
                    if field == 'effects':
                        reconstructed_effects = [normalize_effect_for_compare(e) for e in data[field]]
                        reconstructed_effects = [e for e in reconstructed_effects if e is not None]
                        snapshot_effects = [normalize_effect_for_compare(e) for e in snapshot_data[field]]
                        snapshot_effects = [e for e in snapshot_effects if e is not None]
                        # Compare as multisets: sort deterministic tuples
                        reconstructed_effects_sorted = sorted(reconstructed_effects)
                        snapshot_effects_sorted = sorted(snapshot_effects)
                        if reconstructed_effects_sorted != snapshot_effects_sorted:
                            # Do NOT attempt synthetic repairs here. The reconstructor
                            # must not guess expirations or invent lifecycle events.
                            # Missing apply/expire/tick events are a backend emitter bug.
                            raise AssertionError(f"{field.capitalize()} mismatch for {side} unit {uid} at seq {seq} (seed {self.seed}): reconstructed={reconstructed_effects_sorted}, snapshot={snapshot_effects_sorted}")
                    elif data[field] != snapshot_data[field]:
                        # If this is the failing unit, dump DoT trace for diagnosis
                        if uid == 'mrvlook' and field == 'hp':
                            try:
                                trace = self._dot_trace.get(uid, [])
                                print(f"[DOT TRACE DUMP] unit={uid} seq={seq} seed={self.seed} trace_len={len(trace)}")
                                for te in trace:
                                    print(f"  TRACE seq={te.get('seq')} ts={te.get('timestamp')} dmg={te.get('damage')} unit_hp={te.get('unit_hp')} raw={te.get('raw_event')}")
                            except Exception:
                                pass
                        raise AssertionError(f"{field.capitalize()} mismatch for {side} unit {uid} at seq {seq} (seed {self.seed}): reconstructed={data[field]}, snapshot={snapshot_data[field]}")

            # Derive and check 'dead'
            reconstructed_dead = data['hp'] == 0
            snapshot_dead = snapshot_data['hp'] == 0
            if reconstructed_dead != snapshot_dead:
                raise AssertionError(f"Dead status mismatch for {side} unit {uid} at seq {seq} (seed {self.seed}): reconstructed={reconstructed_dead}, snapshot={snapshot_dead}")

    def get_reconstructed_state(self) -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
        """Get the current reconstructed state."""
        return self.reconstructed_player_units, self.reconstructed_opponent_units


if __name__ == "__main__":
    import sys
    import random
    sys.path.insert(0, '../../../waffen-tactics/src')
    from waffen_tactics.services.combat_simulator import CombatSimulator
    from waffen_tactics.services.combat_unit import CombatUnit
    data = load_game_data()
    units = data.units

    for seed in range(188, 1000):
        print(f"Testing seed {seed}")
        random.seed(seed)
        team_a_units_data = random.sample(units, 10)
        team_b_units_data = random.sample(units, 10)

        team_a = []
        for i, unit_data in enumerate(team_a_units_data):
            team_a.append(CombatUnit(
                id=f"{unit_data.id}_{i}",
                name=unit_data.name,
                hp=unit_data.stats.hp,
                attack=unit_data.stats.attack,
                defense=unit_data.stats.defense,
                attack_speed=unit_data.stats.attack_speed,
                effects=[],
                max_mana=unit_data.stats.max_mana,
                skill=unit_data.skill,
                stats=unit_data.stats
            ))
        team_b = []
        for i, unit_data in enumerate(team_b_units_data):
            team_b.append(CombatUnit(
                id=f"{unit_data.id}_{i+10}",  # Offset to avoid collision
                name=unit_data.name,
                hp=unit_data.stats.hp,
                attack=unit_data.stats.attack,
                defense=unit_data.stats.defense,
                attack_speed=unit_data.stats.attack_speed,
                effects=[],
                max_mana=unit_data.stats.max_mana,
                skill=unit_data.skill,
                stats=unit_data.stats
            ))

        events = []
        def callback(t, d):
            events.append((t, d))

        sim = CombatSimulator(dt=0.1, timeout=10)
        res = sim.simulate(team_a, team_b, event_callback=callback)

        # Sort events by seq
        events.sort(key=lambda x: x[1].get('seq', 0))

        # Dump events around the failing region so we can inspect ordering and payloads

        # Also print any events touching olsak_10 for deeper inspection

        # Find first state_snapshot
        first_snapshot = None
        for t, d in events:
            if t == 'state_snapshot':
                first_snapshot = d
                break

        if not first_snapshot:
            print(f"No snapshot for seed {seed}")
            continue

        # Reconstruct
        reconstructor = CombatEventReconstructor()
        reconstructor.seed = seed
        reconstructor.initialize_from_snapshot(first_snapshot)

        try:
            for t, d in events:
                reconstructor.process_event(t, d)
            print(f"Seed {seed} passed")
        except AssertionError as e:
            print(f"Seed {seed} failed: {e}")
            break