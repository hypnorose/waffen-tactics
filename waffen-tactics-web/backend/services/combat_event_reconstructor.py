"""
Replay canonical combat events and validate optional state checkpoints.

================================================================================
ARCHITECTURAL VIOLATIONS WARNING
================================================================================

The reducer is intentionally strict: combat state must be derivable from the
ordered event stream. Snapshots are validation inputs only.

CORE PRINCIPLE:
    The reconstructor should be a DUMB REPLAY ENGINE that applies events in sequence.
    It should NOT contain formulas, inference logic, or "smart" recovery mechanisms.
    If state cannot be reconstructed from events alone, THE BACKEND IS BROKEN.

Canonical event handlers require event-specific authoritative fields.
They never derive HP, stats, effects, or expiration state from snapshots.
"""
import math
from typing import Dict, List, Any, Tuple
from .combat_snapshot_contract import validate_combat_snapshot


class CombatEventReconstructor:
    """Reconstructs combat game state from a sequence of events."""

    def __init__(self):
        self.reconstructed_player_units: Dict[str, Dict[str, Any]] = {}
        self.reconstructed_opponent_units: Dict[str, Dict[str, Any]] = {}
        self._applied_formation_events: Dict[str, Tuple[str, str, str]] = {}
        self.seed = None

    @staticmethod
    def _require_effect_id(effect_id: Any, context: str) -> str:
        """Require the canonical non-empty string effect identity."""
        if not isinstance(effect_id, str) or not effect_id.strip():
            raise ValueError(f"{context} requires a non-empty string effect_id")
        return effect_id

    @staticmethod
    def _preserve_item_context(effect: Dict[str, Any], event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Copy item identity and stack/value context without deriving state."""
        for field in (
            'item_id', 'item_effect_id', 'item_effect', 'stack', 'stacks',
            'stack_cap', 'value_before', 'value_after',
        ):
            if field in event_data and event_data[field] is not None:
                effect[field] = event_data[field]
        return effect

    @staticmethod
    def _validate_item_context(event_data: Dict[str, Any]) -> None:
        """Reject a partial item identity before any replay mutation."""
        has_item_context = any(
            event_data.get(field) is not None
            for field in ('item_id', 'item_effect_id')
        )
        if not has_item_context:
            return
        for field in ('item_id', 'item_effect_id'):
            value = event_data.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"item event seq={event_data.get('seq')} requires non-empty string {field}"
                )

    def initialize_from_snapshot(self, snapshot_data: Dict[str, Any]):
        """Initialize reconstruction from a state_snapshot event."""
        validate_combat_snapshot(
            snapshot_data,
            context=f"snapshot seq={snapshot_data.get('seq', 'N/A')}"
            if isinstance(snapshot_data, dict) else "snapshot",
        )

        def normalize_unit(u):
            uu = dict(u)
            uu.setdefault('effects', [])
            uu.setdefault('base_stats', {})
            # Ensure canonical fields exist
            for eff in uu['effects']:
                CombatEventReconstructor._require_effect_id(
                    eff.get('id'),
                    f"Snapshot unit {u.get('id')} effect",
                )
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
        self._applied_formation_events = {}

    def process_event(self, event_type: str, event_data: Dict[str, Any]):
        """Process a single event and update the reconstructed state."""
        seq = event_data.get('seq', 'N/A')
        # print(f"Processing event: type={event_type}, seq={seq}")
        self._validate_item_context(event_data)

        if event_type in ['attack', 'unit_attack']:
            self._process_damage_event(event_data)
        elif event_type == 'damage':
            # Redirected damage has the same authoritative HP/shield mutation
            # contract as a hit, but remains explicit for replay diagnostics.
            self._process_damage_event(event_data)
        elif event_type == 'damage_dodged':
            self._process_damage_dodged_event(event_data)
        elif event_type == 'unit_died':
            self._process_unit_death_event(event_data)
        elif event_type == 'mana_update':
            self._process_mana_update_event(event_data)
        elif event_type in ['heal', 'unit_heal']:
            self._process_heal_event(event_data)
        elif event_type == 'shield_applied':
            self._process_shield_applied_event(event_data)
        elif event_type == 'shield_broken':
            self._process_shield_broken_event(event_data)
        elif event_type == 'damage_over_time_tick':
            self._process_dot_event(event_data)
        elif event_type == 'damage_over_time_applied':
            self._process_dot_applied_event(event_data)
        elif event_type == 'effect_applied':
            self._process_effect_applied_event(event_data)
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
        elif event_type == 'regen_gain':
            self._process_regen_gain_event(event_data)
        elif event_type == 'skill_cast':
            self._process_skill_cast_event(event_data)
        elif event_type == 'passive_triggered':
            # Passive events explain the action; authoritative mutations arrive
            # through stat, mana, and effect events in the same stream.
            pass
        elif event_type == 'formation_changed':
            self._process_formation_changed_event(event_data)
        elif event_type in (
            'animation_start',
            'gold_reward',
            # These are transport/control frames.  They do not mutate the
            # reconstructed combat roster, but they are still part of the
            # canonical stream and must be explicit here so the verifier can
            # fail closed when a new control event is introduced.
            'units_init',
            'start',
            'victory',
            'defeat',
            'gold_income',
            'end',
        ):
            # These events are intentionally non-state replay metadata. Keep
            # them explicit so a newly introduced event cannot be swallowed by
            # the default branch below.
            pass
        elif event_type == 'state_snapshot':
            self._process_state_snapshot_event(event_data)
        else:
            raise ValueError(
                f"Unsupported replay event type={event_type} at seq={seq}: {event_data}"
            )

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
        except Exception as exc:
            raise ValueError(
                f"Invalid embedded game_state checkpoint for event_type={event_type} seq={seq}"
            ) from exc

    def _process_damage_event(self, event_data: Dict[str, Any]):
        """Process attack or unit_attack event.

        ``target_hp`` is the canonical post-damage value. HP is never derived
        from the damage amount during replay.
        """
        target_id = event_data.get('target_id')
        damage = event_data.get('damage', 0)
        shield_absorbed = event_data.get('shield_absorbed', 0)

        if target_id is None:
            raise ValueError(f"Damage event missing target_id: {event_data}")
        if 'target_hp' not in event_data or event_data.get('target_hp') is None:
            raise ValueError(
                f"Damage event missing canonical target_hp for target_id={target_id} "
                f"at seq={event_data.get('seq')}: {event_data}"
            )
        new_hp = event_data['target_hp']
        unit_dict = self._get_unit_dict(target_id)
        if unit_dict is None:
            raise ValueError(f"Damage event references unknown target_id={target_id}")
        unit_dict['hp'] = new_hp
        if 'post_shield' in event_data and event_data.get('post_shield') is not None:
            unit_dict['shield'] = event_data['post_shield']
        elif 'unit_shield' in event_data and event_data.get('unit_shield') is not None:
            # Compatibility alias for older event streams. Canonical post_shield
            # always takes precedence when both fields are present.
            unit_dict['shield'] = event_data['unit_shield']
        elif shield_absorbed:
            raise ValueError(
                f"Damage event with shield absorption lacks authoritative post shield at seq={event_data.get('seq')}: {event_data}"
            )

    def _process_damage_dodged_event(self, event_data: Dict[str, Any]):
        """Validate an explicit dodge without applying ordinary hit damage."""
        target_id = event_data.get('target_id') or event_data.get('unit_id')
        attacker_id = event_data.get('attacker_id')
        if not target_id:
            raise ValueError(f"damage_dodged event missing target_id: {event_data}")
        if not attacker_id:
            raise ValueError(f"damage_dodged event missing attacker_id: {event_data}")
        if self._get_unit_dict(target_id) is None:
            raise ValueError(f"damage_dodged references unknown target_id={target_id}")
        if self._get_unit_dict(attacker_id) is None:
            raise ValueError(f"damage_dodged references unknown attacker_id={attacker_id}")

        for field in ('damage', 'applied_damage', 'shield_absorbed'):
            value = event_data.get(field)
            if value is not None and value != 0:
                raise ValueError(
                    f"damage_dodged must be a zero-damage outcome for field={field}: {event_data}"
                )

        # A canonical emitter may include the unchanged post-state. Validate
        # it when present, while keeping the historical seq=84 payload valid
        # even though that production payload had no HP fields.
        target = self._get_unit_dict(target_id)
        for field in ('target_hp', 'post_hp', 'unit_hp'):
            value = event_data.get(field)
            if value is not None and value != target.get('hp'):
                raise ValueError(
                    f"damage_dodged changed target HP in field={field}: {event_data}"
                )
        for field in ('post_shield', 'unit_shield'):
            value = event_data.get(field)
            if value is not None and value != target.get('shield', 0):
                raise ValueError(
                    f"damage_dodged changed target shield in field={field}: {event_data}"
                )

    def _process_unit_death_event(self, event_data: Dict[str, Any]):
        """Process unit_died event."""
        unit_id = event_data.get('unit_id') or event_data.get('caster_id')
        if not unit_id:
            raise ValueError(f"unit_died event missing unit_id: {event_data}")

        unit_dict = self._get_unit_dict(unit_id)
        if unit_dict is None:
            raise ValueError(
                f"unit_died event references unknown unit_id={unit_id} "
                f"at seq={event_data.get('seq')}: {event_data}"
            )

        old_hp = unit_dict['hp']
        unit_dict['hp'] = 0  # Set to 0 when dead
        side = "player" if unit_id in self.reconstructed_player_units else "opponent"
        print(f"  Marked {side} unit {unit_id} as dead")
        if 'olsak' in unit_id:
            print(f"    DEBUG: olsak unit {unit_id} died, HP was {old_hp} before setting to 0")

    def _process_mana_update_event(self, event_data: Dict[str, Any]):
        """Process mana_update event.

        Mana is reconstructed from the authoritative post-state emitted by the
        canonical combat pipeline.  The event amount is explanatory metadata,
        not a replay instruction: applying it here would conceal a malformed
        or truncated event stream.
        """
        unit_id = event_data.get('unit_id')
        if not unit_id:
            raise ValueError(f"mana_update event missing unit_id: {event_data}")
        unit_dict = self._get_unit_dict(unit_id)
        if not unit_dict:
            raise ValueError(f"mana_update references unknown unit_id={unit_id}: {event_data}")

        # Both canonical emitters are supported: emit_mana_change publishes
        # post_mana and current_mana, while the legacy-named emit_mana_update
        # publishes current_mana.  Neither permits an amount-only fallback.
        if 'post_mana' in event_data and event_data.get('post_mana') is not None:
            unit_dict['current_mana'] = event_data['post_mana']
        elif 'current_mana' in event_data and event_data.get('current_mana') is not None:
            unit_dict['current_mana'] = event_data['current_mana']
        else:
            raise ValueError(
                f"mana_update missing canonical current_mana/post_mana for "
                f"unit_id={unit_id} at seq={event_data.get('seq')}: {event_data}"
            )

    def _process_heal_event(self, event_data: Dict[str, Any]):
        """Process heal or unit_heal event.

        ``post_hp`` is the canonical post-heal value. HP is never derived from
        the heal amount during replay.
        """
        unit_id = event_data.get('unit_id')
        amount = event_data.get('amount')
        if not unit_id:
            raise ValueError(f"Heal event missing unit_id: {event_data}")
        unit_dict = self._get_unit_dict(unit_id)
        if unit_dict is None:
            raise ValueError(
                f"Heal event references unknown unit_id={unit_id} "
                f"at seq={event_data.get('seq')}: {event_data}"
            )

        if 'post_hp' not in event_data or event_data.get('post_hp') is None:
            raise ValueError(
                f"Heal event missing canonical post_hp for unit_id={unit_id} "
                f"at seq={event_data.get('seq')}: {event_data}"
            )
        unit_dict['hp'] = event_data['post_hp']


    def _process_shield_applied_event(self, event_data: Dict[str, Any]):
        """Process shield_applied event."""
        unit_id = event_data.get('unit_id')
        amount = event_data.get('amount')
        duration = event_data.get('duration')
        if not unit_id:
            raise ValueError(f"shield_applied event missing unit_id: {event_data}")
        if amount is None:
            raise ValueError(f"shield_applied event missing amount: {event_data}")
        effect_id = self._require_effect_id(
            event_data.get('effect_id'),
            f"shield_applied event seq={event_data.get('seq')}",
        )
        unit_dict = self._get_unit_dict(unit_id)
        if unit_dict is None:
            raise ValueError(f"shield_applied references unknown unit_id={unit_id}")
        if 'post_shield' not in event_data or event_data.get('post_shield') is None:
            raise ValueError(
                f"shield_applied missing canonical post_shield for unit_id={unit_id} "
                f"at seq={event_data.get('seq')}: {event_data}"
            )
        unit_dict['shield'] = event_data['post_shield']
        # Add shield effect
        eid = effect_id
        effect = self._preserve_item_context({
            'id': eid,
            'type': 'shield',
            'amount': amount,
            'duration': duration,
            'source': event_data.get('source', unit_id),
            'expires_at': event_data.get('timestamp', 0) + (duration or 0),
            'applied_amount': amount  # Store for reversion
        }, event_data)
        unit_dict['effects'].append(effect)
        print(f"  Applied shield to unit {unit_id}: post_shield={unit_dict['shield']}")

    def _process_shield_broken_event(self, event_data: Dict[str, Any]):
        """Apply the authoritative shield removal and clear its effect."""
        unit_id = event_data.get('unit_id') or event_data.get('target_id')
        amount = event_data.get('amount')
        if not unit_id:
            raise ValueError(f"shield_broken event missing unit_id: {event_data}")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(float(amount)) or amount <= 0:
            raise ValueError(f"shield_broken event requires positive amount: {event_data}")
        unit_dict = self._get_unit_dict(unit_id)
        if unit_dict is None:
            raise ValueError(f"shield_broken references unknown unit_id={unit_id}")
        for field in ('post_shield', 'unit_shield'):
            if field in event_data and event_data.get(field) != 0:
                raise ValueError(
                    f"shield_broken must leave target shield at zero in field={field}: {event_data}"
                )
        unit_dict['shield'] = 0
        unit_dict['effects'] = [
            effect for effect in unit_dict.get('effects', [])
            if not (isinstance(effect, dict) and effect.get('type') == 'shield')
        ]

    def _process_dot_event(self, event_data: Dict[str, Any]):
        """Process damage_over_time_tick event.

        ``post_hp`` is the canonical post-tick value. The reconstructor does
        not deduplicate events or calculate damage.
        """
        unit_id = event_data.get('unit_id')
        damage = event_data.get('damage', 0)

        if not unit_id:
            raise ValueError(f"DoT tick missing unit_id: {event_data}")

        unit_dict = self._get_unit_dict(unit_id)
        if unit_dict is None:
            raise ValueError(f"DoT tick references unknown unit_id={unit_id}")

        if 'post_hp' not in event_data or event_data.get('post_hp') is None:
            raise ValueError(
                f"DoT tick missing canonical post_hp for unit_id={unit_id} "
                f"at seq={event_data.get('seq')}: {event_data}"
            )

        shield_absorbed = event_data.get('shield_absorbed', 0)
        post_shield = event_data.get('post_shield')
        if post_shield is None:
            # Compatibility alias is accepted only at the reconstruction boundary.
            post_shield = event_data.get('unit_shield')
        if shield_absorbed and post_shield is None:
            raise ValueError(
                f"DoT tick with shield absorption lacks authoritative post shield at seq={event_data.get('seq')}: {event_data}"
            )

        old_hp = unit_dict['hp']
        unit_dict['hp'] = event_data['post_hp']
        if post_shield is not None:
            unit_dict['shield'] = post_shield
        print(f"  DoT damage to unit {unit_id}: {old_hp} -> {unit_dict['hp']}")

    def _process_dot_applied_event(self, event_data: Dict[str, Any]):
        """Process damage_over_time_applied event: install canonical DoT effect."""
        unit_id = event_data.get('unit_id')
        if not unit_id:
            raise ValueError(f"DoT application missing unit_id: {event_data}")
        effect_id = self._require_effect_id(
            event_data.get('effect_id'),
            f"damage_over_time_applied event seq={event_data.get('seq')}",
        )
        damage = event_data.get('damage')
        if not isinstance(damage, (int, float)) or isinstance(damage, bool) or not math.isfinite(damage) or damage <= 0:
            raise ValueError(f"DoT application missing canonical damage: {event_data}")
        if event_data.get('expires_at') is None:
            raise ValueError(f"DoT application missing authoritative expires_at: {event_data}")
        unit_dict = self._get_unit_dict(unit_id)
        if unit_dict is None:
            raise ValueError(
                f"DoT application references unknown unit_id={unit_id} "
                f"at seq={event_data.get('seq')}: {event_data}"
            )
        # Build canonical effect object matching snapshot shape
        eff = self._preserve_item_context({
            'id': effect_id,
            'type': 'damage_over_time',
            'damage': damage,
            'damage_type': event_data.get('damage_type'),
            'interval': event_data.get('interval'),
            'ticks_remaining': event_data.get('ticks'),
            'total_ticks': event_data.get('ticks'),
            'next_tick_time': event_data.get('next_tick_time'),
            'expires_at': event_data.get('expires_at'),
            'source': event_data.get('source') or event_data.get('caster_id') or event_data.get('caster_name')
        }, event_data)
        unit_dict.setdefault('effects', [])
        # Avoid duplicates by id
        existing_ids = {e.get('id') for e in unit_dict.get('effects', []) if e.get('id')}
        if eff.get('id') not in existing_ids:
            unit_dict['effects'].append(eff)
            print(f"  Applied DoT effect to unit {unit_id}: effect_id={eff.get('id')}, damage={eff.get('damage')}")

    def _process_effect_applied_event(self, event_data: Dict[str, Any]):
        """Install a complete non-specialized effect from its canonical event."""
        unit_id = event_data.get('unit_id')
        effect_id = self._require_effect_id(
            event_data.get('effect_id'),
            f"effect_applied event seq={event_data.get('seq')}",
        )
        effect_data = event_data.get('effect')
        if not unit_id:
            raise ValueError(f"effect_applied event missing unit_id: {event_data}")
        if not isinstance(effect_data, dict):
            raise ValueError(f"effect_applied event missing effect object: {event_data}")
        if not isinstance(effect_data.get('type'), str) or not effect_data.get('type').strip():
            raise ValueError(f"effect_applied event missing effect object type: {event_data}")
        effect_object_id = self._require_effect_id(
            effect_data.get('id'),
            f"effect_applied event seq={event_data.get('seq')} effect object",
        )

        unit_dict = self._get_unit_dict(unit_id)
        if unit_dict is None:
            raise ValueError(f"effect_applied references unknown unit_id={unit_id}")

        effect = self._preserve_item_context(dict(effect_data), event_data)
        if effect_object_id != effect_id:
            raise ValueError(
                f"effect_applied effect id mismatch at seq={event_data.get('seq')}: "
                f"payload={effect_id}, effect={effect.get('id')}"
            )
        existing_ids = {e.get('id') for e in unit_dict.get('effects', []) if isinstance(e, dict)}
        if effect_id in existing_ids:
            raise ValueError(
                f"effect_applied duplicates effect_id={effect_id} on unit={unit_id} "
                f"at seq={event_data.get('seq')}"
            )
        unit_dict.setdefault('effects', []).append(effect)
    def _process_skill_cast_event(self, event_data: Dict[str, Any]):
        """Legacy no-op for old replay payloads that still mention skill_cast."""
        return

    def _process_formation_changed_event(self, event_data: Dict[str, Any]):
        """Apply an authoritative formation transition without toggling it."""
        unit_id = event_data.get('unit_id')
        if not unit_id:
            raise ValueError(
                f"formation_changed event missing unit_id at seq={event_data.get('seq')}"
            )

        event_id = event_data.get('event_id')
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError(
                f"formation_changed event missing event_id at seq={event_data.get('seq')}"
            )

        previous_position = event_data.get('previous_position')
        new_position = event_data.get('new_position')
        if previous_position not in ('front', 'back') or new_position not in ('front', 'back'):
            raise ValueError(
                f"formation_changed event has invalid positions at seq={event_data.get('seq')}: "
                f"previous={previous_position!r}, new={new_position!r}"
            )
        if previous_position == new_position:
            raise ValueError(
                f"formation_changed event has no transition at seq={event_data.get('seq')}"
            )

        transition = (unit_id, previous_position, new_position)
        applied_transition = self._applied_formation_events.get(event_id)
        if applied_transition is not None:
            if applied_transition != transition:
                raise ValueError(
                    f"formation_changed conflicting duplicate event_id={event_id} "
                    f"at seq={event_data.get('seq')}"
                )
            return

        unit_dict = self._get_unit_dict(unit_id)
        if unit_dict is None:
            raise ValueError(
                f"formation_changed references unknown unit_id={unit_id} "
                f"at seq={event_data.get('seq')}"
            )

        current_position = unit_dict.get('position')
        if current_position != previous_position:
            raise ValueError(
                f"formation_changed position mismatch for unit_id={unit_id} "
                f"at seq={event_data.get('seq')}: expected current={previous_position!r}, "
                f"actual={current_position!r}"
            )
        unit_dict['position'] = new_position
        self._applied_formation_events[event_id] = transition

    def _process_stat_buff_event(self, event_data: Dict[str, Any]):
        """Process stat_buff event.

        Requires authoritative 'applied_delta' from backend to properly apply stat changes.
        If applied_delta is missing, the event cannot be processed reliably.

        The reconstructor should NOT compute percentage buffs or guess random stats.
        This is GAME LOGIC that belongs in the backend emitter.
        """
        unit_id = event_data.get('unit_id')
        stat = event_data.get('stat')
        value = event_data.get('value')
        amount = event_data.get('amount', value)
        value_type = event_data.get('value_type', 'flat')
        duration = event_data.get('duration')
        effect_id = self._require_effect_id(
            event_data.get('effect_id'),
            f"stat_buff event seq={event_data.get('seq')}",
        )

        if not unit_id:
            raise ValueError(f"stat_buff event missing unit_id: {event_data}")

        unit_dict = self._get_unit_dict(unit_id)
        if not unit_dict:
            raise ValueError(f"stat_buff references unknown unit_id={unit_id}")

        delta = event_data.get('applied_delta')
        if delta is None:
            raise ValueError(
                f"stat_buff event missing authoritative applied_delta at seq={event_data.get('seq')}: {event_data}"
            )
        if not stat or stat == 'random':
            raise ValueError(
                f"stat_buff event lacks a concrete stat at seq={event_data.get('seq')}: {event_data}"
            )

        # Effect identity is part of the canonical event contract.
        eid = effect_id

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

        effect = self._preserve_item_context({
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
        }, event_data)
        unit_dict['effects'].append(effect)

    def _process_hp_regen_event(self, event_data: Dict[str, Any]):
        """Process hp_regen event."""
        unit_id = event_data.get('unit_id')
        amount = event_data.get('amount')
        if not unit_id:
            raise ValueError(f"HP regen event missing unit_id: {event_data}")
        unit_dict = self._get_unit_dict(unit_id)
        if unit_dict is None:
            raise ValueError(
                f"HP regen event references unknown unit_id={unit_id} "
                f"at seq={event_data.get('seq')}: {event_data}"
            )

        if 'post_hp' not in event_data or event_data.get('post_hp') is None:
            raise ValueError(
                f"HP regen event missing canonical post_hp for unit_id={unit_id} "
                f"at seq={event_data.get('seq')}: {event_data}"
            )
        unit_dict['hp'] = event_data['post_hp']
        # print(f"  Regenerated HP for unit {unit_id} from {old_hp} to {unit_dict['hp']}")

    def _process_regen_gain_event(self, event_data: Dict[str, Any]):
        """Apply the authoritative post-state of an HP-regen source."""
        unit_id = event_data.get('unit_id')
        if not unit_id:
            raise ValueError(f"HP regen gain event missing unit_id: {event_data}")
        unit_dict = self._get_unit_dict(unit_id)
        if unit_dict is None:
            raise ValueError(
                f"HP regen gain event references unknown unit_id={unit_id} "
                f"at seq={event_data.get('seq')}: {event_data}"
            )

        post_regen = event_data.get('post_hp_regen_per_sec')
        if (
            isinstance(post_regen, bool)
            or not isinstance(post_regen, (int, float))
            or not math.isfinite(float(post_regen))
        ):
            raise ValueError(
                f"HP regen gain event missing canonical post_hp_regen_per_sec "
                f"for unit_id={unit_id} at seq={event_data.get('seq')}: {event_data}"
            )

        buffed_stats = dict(unit_dict.get('buffed_stats') or {})
        buffed_stats['hp_regen_per_sec'] = post_regen
        unit_dict['buffed_stats'] = buffed_stats

    def _process_stun_event(self, event_data: Dict[str, Any]):
        """Process unit_stunned event."""
        unit_id = event_data.get('unit_id')
        duration = event_data.get('duration')
        source = event_data.get('source') or event_data.get('source_id')
        timestamp = event_data.get('timestamp', 0)
        if not unit_id:
            raise ValueError(f"unit_stunned event missing unit_id: {event_data}")
        effect_id = self._require_effect_id(
            event_data.get('effect_id'),
            f"unit_stunned event seq={event_data.get('seq')}",
        )
        unit_dict = self._get_unit_dict(unit_id)
        if not unit_dict:
            raise ValueError(f"unit_stunned references unknown unit_id={unit_id}")
        # Create a canonical stun effect entry similar to emitter shape
        eff = self._preserve_item_context({
            'id': effect_id,
            'type': 'stun',
            'duration': duration,
            'source': source,
            'expires_at': (timestamp + float(duration)) if (duration and duration > 0) else None,
        }, event_data)
        unit_dict.setdefault('effects', [])
        unit_dict['effects'].append(eff)
        print(f"  Reconstructed stun on unit {unit_id}: duration={duration}, source={source}")
    def _process_dot_expired_event(self, event_data: Dict[str, Any]):
        """Process damage_over_time_expired event: remove canonical DoT effect."""
        unit_id = event_data.get('unit_id')
        effect_id = self._require_effect_id(
            event_data.get('effect_id'),
            f"damage_over_time_expired event seq={event_data.get('seq')}",
        )
        if not unit_id:
            raise ValueError(f"damage_over_time_expired event missing unit_id: {event_data}")
        unit_dict = self._get_unit_dict(unit_id)
        if unit_dict is None:
            raise ValueError(
                f"damage_over_time_expired references unknown unit_id={unit_id}: {event_data}"
            )
        if 'post_hp' not in event_data or event_data.get('post_hp') is None:
            raise ValueError(
                f"damage_over_time_expired missing canonical post_hp for "
                f"unit_id={unit_id}, effect_id={effect_id} at seq={event_data.get('seq')}: {event_data}"
            )

        effs = unit_dict.get('effects') or []
        if not any(e.get('id') == effect_id for e in effs):
            raise ValueError(
                f"damage_over_time_expired references missing effect_id={effect_id} "
                f"on unit={unit_id} at seq={event_data.get('seq')}"
            )

        # Validate the complete event before mutating replay state.
        new_eff = [e for e in effs if e.get('id') != effect_id]
        unit_dict['effects'] = new_eff
        print(f"  Removed DoT effect from unit {unit_id}: effect_id={effect_id}")
        old_hp = unit_dict.get('hp')
        unit_dict['hp'] = event_data['post_hp']
        print(f"  DoT expire updated unit {unit_id} HP: {old_hp} -> {unit_dict['hp']}")

    def _process_effect_expired_event(self, event_data: Dict[str, Any]):
        unit_id = event_data.get('unit_id')
        effect_id = self._require_effect_id(
            event_data.get('effect_id'),
            f"effect_expired event seq={event_data.get('seq')}",
        )
        if not unit_id:
            raise ValueError(f"effect_expired event missing unit_id: {event_data}")
        unit_dict = self._get_unit_dict(unit_id)
        if unit_dict is None:
            raise ValueError(f"effect_expired references unknown unit_id={unit_id}: {event_data}")
        effs = unit_dict.get('effects') or []
        if not any(e.get('id') == effect_id for e in effs):
            raise ValueError(
                f"effect_expired references missing effect_id={effect_id} on unit={unit_id} "
                f"at seq={event_data.get('seq')}"
            )

        # Validate every authoritative post-state value before mutating replay.
        if 'post_hp' not in event_data or event_data.get('post_hp') is None:
            raise ValueError(
                f"effect_expired missing canonical post_hp for unit_id={unit_id}, "
                f"effect_id={effect_id} at seq={event_data.get('seq')}: {event_data}"
            )
        stat = event_data.get('stat')
        if stat:
            key = f'post_{stat}'
            if key not in event_data or event_data.get(key) is None:
                raise ValueError(
                    f"effect_expired missing canonical {key} for unit_id={unit_id}, "
                    f"effect_id={effect_id} at seq={event_data.get('seq')}: {event_data}"
                )
        if event_data.get('effect_type') == 'shield' or 'post_shield' in event_data:
            if 'post_shield' not in event_data or event_data.get('post_shield') is None:
                raise ValueError(
                    f"effect_expired missing canonical post_shield for unit_id={unit_id}, "
                    f"effect_id={effect_id} at seq={event_data.get('seq')}: {event_data}"
                )

        # All validation has passed; apply the expiration atomically.
        new_eff = [e for e in effs if e.get('id') != effect_id]
        unit_dict['effects'] = new_eff
        print(f"  Removed effect from unit {unit_id}: effect_id={effect_id}")
        if stat:
            key = f'post_{stat}'
            unit_dict[stat] = event_data[key]
        if event_data.get('effect_type') == 'shield' or 'post_shield' in event_data:
            unit_dict['shield'] = event_data['post_shield']
        old_hp = unit_dict.get('hp')
        unit_dict['hp'] = event_data['post_hp']
        print(f"  Effect expire updated unit {unit_id} HP: {old_hp} -> {unit_dict['hp']}")
        # NOTE: previously this handler incorrectly appended a stun effect
        # unconditionally. An "effect_expired" event should only remove the
        # described effect (and optionally update authoritative HP). Stuns
        # are reconstructed from `unit_stunned` events; do not create new
        # effects here.

    def _process_state_snapshot_event(self, event_data: Dict[str, Any]):
        # print(f"  Checking state_snapshot at seq {event_data.get('seq', 'N/A')}")

        validate_combat_snapshot(
            event_data,
            context=f"state_snapshot seq={event_data.get('seq', 'N/A')}",
        )

        current_time = event_data.get('timestamp', 0)

        # Create snapshot copies for comparison
        snapshot_player_units = {
            u['id']: dict(u)  # Remove 'dead' derivation
            for u in event_data['player_units']
        }
        snapshot_opponent_units = {
            u['id']: dict(u)  # Remove 'dead' derivation
            for u in event_data['opponent_units']
        }

        # A snapshot is a validation checkpoint, never an input to replay.
        # Keep the legacy reconciliation implementation below unreachable until
        # it is deleted; allowing it to run would mask missing canonical events.
        self._compare_units(
            self.reconstructed_player_units,
            snapshot_player_units,
            "player",
            event_data.get('seq', 'N/A'),
            current_time,
        )
        self._compare_units(
            self.reconstructed_opponent_units,
            snapshot_opponent_units,
            "opponent",
            event_data.get('seq', 'N/A'),
            current_time,
        )
        return

    def _get_unit_dict(self, unit_id: str) -> Dict[str, Any]:
        if unit_id in self.reconstructed_player_units:
            return self.reconstructed_player_units[unit_id]
        elif unit_id in self.reconstructed_opponent_units:
            return self.reconstructed_opponent_units[unit_id]
        return None

    def _compare_units(self, reconstructed: Dict[str, Dict], snapshot: Dict[str, Dict], side: str, seq: Any, current_time: float = 0):
        def normalize_effect_for_compare(effect):
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
                        raise AssertionError(f"{field.capitalize()} mismatch for {side} unit {uid} at seq {seq} (seed {self.seed}): reconstructed={data[field]}, snapshot={snapshot_data[field]}")

            # Derive and check 'dead'
            reconstructed_dead = data['hp'] == 0
            snapshot_dead = snapshot_data['hp'] == 0
            if reconstructed_dead != snapshot_dead:
                raise AssertionError(f"Dead status mismatch for {side} unit {uid} at seq {seq} (seed {self.seed}): reconstructed={reconstructed_dead}, snapshot={snapshot_dead}")

    def get_reconstructed_state(self) -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
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
