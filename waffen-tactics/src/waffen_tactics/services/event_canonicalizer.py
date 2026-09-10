import time as _time
import uuid
from typing import Optional, Dict, Any, Callable, List


def _now_ts():
    return _time.time()


def _deliver_canonical_event(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    event_type: str,
    payload: Dict[str, Any],
) -> None:
    """Deliver a canonical event without hiding downstream failures."""
    if event_callback is not None:
        event_callback(event_type, payload)


def _require_non_empty_effect_id(effect_id: Any, event_type: str) -> str:
    """Reject lifecycle events that cannot identify their effect."""
    if not isinstance(effect_id, str) or not effect_id.strip():
        raise ValueError(f"{event_type} requires a non-empty string effect_id")
    return effect_id


def emit_effect_applied(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    recipient: Any,
    effect: Dict[str, Any],
    source: Optional[Any] = None,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
):
    """Atomically install and emit a canonical non-specialized effect."""
    if not isinstance(effect, dict):
        raise ValueError("effect_applied requires an effect dictionary")

    ts = timestamp if timestamp is not None else _now_ts()
    canonical_effect = dict(effect)
    effect_id = canonical_effect.get('id') or str(uuid.uuid4())
    canonical_effect['id'] = effect_id
    if source is not None:
        canonical_effect.setdefault('source', getattr(source, 'id', None))

    duration = canonical_effect.get('duration')
    if canonical_effect.get('expires_at') is None and duration and float(duration) > 0:
        canonical_effect['expires_at'] = ts + float(duration)

    had_effects_attr = hasattr(recipient, 'effects')
    effects = list(getattr(recipient, 'effects', []) or [])
    previous_effects = list(effects)
    replaced = [
        existing for existing in effects
        if not (
            isinstance(existing, dict)
            and existing.get('source') == canonical_effect.get('source')
            and existing.get('passive_effect') == canonical_effect.get('passive_effect')
        )
    ]
    removed = [existing for existing in effects if existing not in replaced]
    final_effects = replaced + [canonical_effect]

    def _rollback_partial_mutation():
        """Restore the exact pre-emission effect collection."""
        rollback_errors = []
        try:
            if had_effects_attr:
                current_effects = list(getattr(recipient, 'effects', []) or [])
                if current_effects != previous_effects:
                    recipient.effects = list(previous_effects)
            elif hasattr(recipient, 'effects'):
                delattr(recipient, 'effects')
        except Exception as rollback_error:
            rollback_errors.append(rollback_error)

        try:
            current_effects = list(getattr(recipient, 'effects', []) or [])
            if current_effects != previous_effects:
                rollback_errors.append(RuntimeError('effect collection rollback postcondition failed'))
        except Exception as rollback_error:
            rollback_errors.append(rollback_error)
        return rollback_errors

    # Commit the complete replacement before delivering any lifecycle event.
    # This prevents an expiration event from being published for a replacement
    # that failed to install.
    try:
        recipient.effects = final_effects
        actual_effects = list(getattr(recipient, 'effects', []) or [])
        if actual_effects != final_effects:
            raise RuntimeError(
                f"emit_effect_applied postcondition failed: replacement not installed on unit={getattr(recipient, 'id', None)}"
            )
    except Exception as exc:
        rollback_errors = _rollback_partial_mutation()
        if rollback_errors:
            raise RuntimeError(
                f"emit_effect_applied mutation failed and rollback was incomplete for unit={getattr(recipient, 'id', None)}"
            ) from exc
        raise RuntimeError(
            f"emit_effect_applied mutation failed for unit={getattr(recipient, 'id', None)}"
        ) from exc

    # Preserve the successful event order: replacement expirations precede the
    # new application event. The state is already committed and verified.
    for old_effect in removed:
        old_id = old_effect.get('id') if isinstance(old_effect, dict) else None
        if old_id:
            emit_effect_expired(
                event_callback,
                recipient,
                old_id,
                unit_hp=getattr(recipient, 'hp', None),
                side=side,
                timestamp=ts,
                effect_type=old_effect.get('type'),
                stat=old_effect.get('stat'),
                applied_delta=old_effect.get('applied_delta'),
                applied_amount=old_effect.get('applied_amount'),
            )

    payload = {
        'unit_id': getattr(recipient, 'id', None),
        'unit_name': getattr(recipient, 'name', None),
        'effect_id': effect_id,
        'effect_type': canonical_effect.get('type'),
        'effect': canonical_effect,
        'source_id': canonical_effect.get('source'),
        'caster_id': canonical_effect.get('source'),
        'caster_name': getattr(source, 'name', None) if source is not None else None,
        'side': side,
        'timestamp': ts,
    }
    _deliver_canonical_event(event_callback, 'effect_applied', payload)
    return payload


def emit_stat_buff(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    recipient: Any,
    stat: str,
    value: float,
    value_type: str = 'flat',
    duration: Optional[float] = None,
    permanent: bool = False,
    source: Optional[Any] = None,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
    cause: Optional[str] = None,
):
    """Canonicalize a stat_buff event and (optionally) mutate recipient state.

    - Mutates numeric fields on recipient for immediate effects.
    - Attaches an effect object to recipient.effects when duration provided.
    - Calls event_callback with canonical payload:
      { unit_id, unit_name, stat, value, value_type, duration, permanent, effect_id?, side, timestamp, cause, source_id }
    """
    ts = timestamp if timestamp is not None else _now_ts()
    try:
        print(f"[EMIT_STAT_BUFF] recipient={getattr(recipient,'id',None)} stat={stat} value={value} event_callback_set={event_callback is not None}")
    except Exception:
        pass

    # Snapshot every field this emitter may touch before establishing the
    # effects collection. A failed effect installation must not leave the
    # immediate stat mutation behind without its canonical effect.
    tracked_attributes = [stat, 'effects']
    if stat in ('hp', 'max_hp'):
        tracked_attributes.append('hp')
    snapshots = {}
    for attribute in dict.fromkeys(tracked_attributes):
        try:
            had_attribute = hasattr(recipient, attribute)
            snapshots[attribute] = (had_attribute, getattr(recipient, attribute, None))
        except Exception as exc:
            raise RuntimeError(
                f"emit_stat_buff state read failed for unit={getattr(recipient, 'id', None)} stat={stat}"
            ) from exc

    def _rollback_partial_mutation():
        """Restore all pre-emission fields that this emitter can mutate."""
        rollback_errors = []
        for attribute, (had_attribute, previous_value) in reversed(list(snapshots.items())):
            try:
                if had_attribute:
                    if getattr(recipient, attribute, None) != previous_value:
                        setattr(recipient, attribute, previous_value)
                elif hasattr(recipient, attribute):
                    delattr(recipient, attribute)
            except Exception as rollback_error:
                rollback_errors.append((attribute, rollback_error))

        for attribute, (_had_attribute, previous_value) in snapshots.items():
            try:
                current_value = getattr(recipient, attribute, None)
                if current_value != previous_value:
                    rollback_errors.append((attribute, RuntimeError('rollback postcondition failed')))
            except Exception as rollback_error:
                rollback_errors.append((attribute, rollback_error))
        return rollback_errors

    # Ensure recipient.effects exists
    if not hasattr(recipient, 'effects') or recipient.effects is None:
        recipient.effects = []

    # If this is a live emission (has an event_callback), avoid applying
    # buffs to already-dead units. For dry-run usage (event_callback is
    # None) we still want to return a canonical payload so callers that
    # generate events offline (tests, previews) can inspect expected
    # payloads even if the in-memory unit was previously marked dead.
    if getattr(recipient, '_dead', False) and event_callback is not None:
        return None

    # CRITICAL: Generate effect_id for ALL stat buffs (even instant ones)
    # This ensures frontend can always track effects with proper IDs
    effect_id = str(uuid.uuid4())

    # Apply immediate numeric mutation when appropriate
    # CRITICAL: Always calculate delta for ALL stats (needed for reconstructor)
    delta = None
    pre_hp = None
    post_hp = None
    try:
        def set_and_verify(attribute, expected_value):
            setattr(recipient, attribute, expected_value)
            actual_value = getattr(recipient, attribute)
            if actual_value != expected_value:
                raise RuntimeError(
                    f"emit_stat_buff {attribute} mutation did not apply for unit={getattr(recipient, 'id', None)}"
                )

        if stat in ('attack', 'defense'):
            if value_type == 'percentage':
                delta = int(round(getattr(recipient, stat, 0) * (float(value) / 100.0)))
            else:
                delta = int(round(value))
            # For temporary buffs with no handler system, still apply the
            # immediate numeric change just as before.
            set_and_verify(stat, getattr(recipient, stat, 0) + delta)
        elif stat == 'hp':
            # delegate hp changes to emit_heal for canonical emission
            if value_type == 'percentage':
                delta = int(round(getattr(recipient, 'hp', 0) * (float(value) / 100.0)))
            else:
                delta = int(round(value))
            emit_heal(event_callback, recipient, delta, source=source, side=side, timestamp=ts)
            post_hp = int(getattr(recipient, 'hp'))
        elif stat in ('attack_speed', 'lifesteal', 'damage_reduction', 'hp_regen_per_sec'):
            # float fields
            cur = float(getattr(recipient, stat, 0.0))
            if value_type == 'percentage' and stat == 'attack_speed':
                delta = round(cur * (float(value) / 100.0), 6)
            else:
                delta = int(round(float(value)))
            set_and_verify(stat, cur + delta)
        elif stat in ('max_hp', 'max_mana', 'current_mana'):
            # int fields
            old_value = int(getattr(recipient, stat, 0) or 0)
            if value_type == 'percentage':
                delta = int(round(old_value * (float(value) / 100.0)))
            else:
                delta = int(round(value))
            new_value = old_value + delta
            if stat == 'max_hp':
                # Max HP changes preserve the unit's current health ratio.
                # A full-health unit stays full, while a damaged unit keeps
                # the same percentage of its new maximum.
                pre_hp = int(getattr(recipient, 'hp', 0) or 0)
                new_max_hp = max(0, new_value)
                if old_value > 0:
                    post_hp = min(new_max_hp, int(round(pre_hp * new_max_hp / old_value)))
                else:
                    post_hp = min(new_max_hp, pre_hp)
                set_and_verify(stat, new_max_hp)
                set_and_verify('hp', post_hp)
            else:
                set_and_verify(stat, new_value)
        else:
            # Unknown/custom stats - still calculate delta for event
            if value_type == 'percentage':
                # Try to get base value, default to 0
                base = getattr(recipient, stat, 0) or 0
                delta = int(round(float(base) * (float(value) / 100.0)))
            else:
                delta = int(round(value)) if isinstance(value, (int, float)) else 0
        # other stats are stored as-is in effects and may be applied by UI recompute
        # Attach and verify the persistent effect in the same transaction as
        # the immediate stat mutation.
        if duration is not None or permanent:
            effect = {
                'id': effect_id,
                'type': 'buff' if (value is None or value >= 0) else 'debuff',
                'stat': stat,
                'value': value,
                'value_type': value_type,
                'applied_delta': delta,
                'duration': duration,
                'permanent': permanent,
                'source': getattr(source, 'id', None) if source is not None else None,
                'expires_at': (ts + duration) if (duration and duration > 0) else None,
            }
            expected_effects = list(getattr(recipient, 'effects', [])) + [effect]
            recipient.effects = expected_effects

            # Fail-fast invariant: active buff effect must be present on recipient.
            actual_effects = list(getattr(recipient, 'effects', []) or [])
            if actual_effects != expected_effects or not any(
                isinstance(active_effect, dict) and active_effect.get('id') == effect_id
                for active_effect in actual_effects
            ):
                raise RuntimeError(
                    f"emit_stat_buff postcondition failed: missing effect_id={effect_id} on unit={getattr(recipient, 'id', None)}"
                )
    except Exception as e:
        rollback_errors = _rollback_partial_mutation()
        if rollback_errors:
            raise RuntimeError(
                f"emit_stat_buff mutation failed and rollback was incomplete for unit={getattr(recipient, 'id', None)} stat={stat}"
            ) from e
        raise RuntimeError(
            f"emit_stat_buff mutation failed for unit={getattr(recipient, 'id', None)} stat={stat}"
        ) from e

    payload = {
        'unit_id': getattr(recipient, 'id', None),
        'unit_name': getattr(recipient, 'name', None),
        'stat': stat,
        'value': value,
        'amount': int(value) if isinstance(value, (int, float)) else value,
        'value_type': value_type,
        'duration': duration,
        'permanent': permanent,
        'effect_id': effect_id,
        'side': side,
        'timestamp': ts,
        'cause': cause,
        'source_id': getattr(source, 'id', None) if source is not None else None,
        'caster_id': getattr(source, 'id', None) if source is not None else None,
        'caster_name': getattr(source, 'name', None) if source is not None else None,
    }
    # include applied_delta when present for deterministic reversion
    payload['applied_delta'] = delta
    if stat == 'max_hp':
        payload['pre_hp'] = pre_hp
        payload['post_hp'] = post_hp

    if event_callback:
        print(f"[EMIT_STAT_BUFF] calling callback for recipient={getattr(recipient,'id',None)}")
    _deliver_canonical_event(event_callback, 'stat_buff', payload)
    if event_callback:
        print(f"[EMIT_STAT_BUFF] callback returned for recipient={getattr(recipient,'id',None)}")

    return payload


def apply_effect_expiration_mutation(
    target: Any,
    stat: str,
    new_value: int,
    new_hp: Optional[int] = None,
) -> Dict[str, int]:
    """Apply an HP-related effect reversion through the canonical mutation path.

    Effect expiration is not a heal or damage event, so it must not synthesize
    either event just to get an authorized HP write.  This helper keeps that
    mutation inside the canonicalizer while preserving the max-HP ratio
    calculated by the simulator.
    """
    if stat not in ('hp', 'max_hp'):
        raise ValueError(f"Unsupported expiration mutation stat: {stat}")

    set_hp = getattr(target, '_set_hp', None)
    if not callable(set_hp):
        raise TypeError(
            f"Expiration mutation target={getattr(target, 'id', None)} does not expose canonical HP setter"
        )

    if stat == 'max_hp':
        if new_hp is None:
            raise ValueError('max_hp expiration mutation requires the post-reversion HP')
        setattr(target, 'max_hp', int(new_value))
        set_hp(int(new_hp), caller_module='event_canonicalizer')
    else:
        set_hp(int(new_value), caller_module='event_canonicalizer')

    return {
        'post_value': int(getattr(target, stat)),
        'post_hp': int(getattr(target, 'hp')),
    }


def _set_and_verify_canonical_hp(recipient: Any, expected_hp: int) -> None:
    """Apply HP through the canonical boundary and verify the resulting state.

    Canonical events must never describe a mutation that was rejected or
    ignored by the recipient. Let setter/getter failures propagate so the
    enclosing combat operation can fail closed before any success event is
    emitted.
    """
    recipient.hp = expected_hp
    actual_hp = int(getattr(recipient, 'hp'))
    if actual_hp != expected_hp:
        raise RuntimeError(
            f"Canonical HP mutation did not apply for unit={getattr(recipient, 'id', None)}: "
            f"expected={expected_hp}, actual={actual_hp}"
        )


def _set_and_verify_canonical_mana(recipient: Any, expected_mana: Any) -> None:
    """Apply mana through the canonical boundary and verify the result."""
    set_mana = getattr(recipient, '_set_mana', None)
    if callable(set_mana):
        set_mana(expected_mana, caller_module='event_canonicalizer')
    else:
        recipient.mana = expected_mana

    actual_mana = getattr(recipient, 'mana')
    if actual_mana != expected_mana:
        raise RuntimeError(
            f"Canonical mana mutation did not apply for unit={getattr(recipient, 'id', None)}: "
            f"expected={expected_mana}, actual={actual_mana}"
        )


def emit_heal(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    recipient: Any,
    amount: float,
    source: Optional[Any] = None,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
    cause: Optional[str] = None,
    current_hp: Optional[int] = None,
):
    """Apply heal to recipient and emit canonical `heal` event.

    Args:
        current_hp: If provided, use this as the authoritative current HP instead of reading from recipient.hp.
                   This is critical when HP lists are updated before calling emit_heal.
    """
    ts = timestamp if timestamp is not None else _now_ts()
    # Use current_hp if provided (authoritative from hp_list), otherwise read
    # from the unit. A failed or ignored mutation must abort before publishing
    # a success-looking canonical event.
    if current_hp is not None:
        cur = int(current_hp)
    else:
        cur = int(getattr(recipient, 'hp', 0))
    max_hp = max(0, int(getattr(recipient, 'max_hp', cur)))
    add = int(amount)
    new = max(0, min(max_hp, cur + add))
    _set_and_verify_canonical_hp(recipient, new)

    payload = {
        'unit_id': getattr(recipient, 'id', None),
        'unit_name': getattr(recipient, 'name', None),
        'amount': int(amount) if amount is not None else None,
        'pre_hp': cur,
        'post_hp': new,
        'unit_hp': new,  # Authoritative HP after heal
        'unit_max_hp': max_hp,
        'side': side,
        'timestamp': ts,
        'cause': cause,
        'source_id': getattr(source, 'id', None) if source is not None else None,
    }
    # If the recipient is dead, do not emit heal events for it
    if getattr(recipient, '_dead', False):
        return None
    _deliver_canonical_event(event_callback, 'heal', payload)
    return payload


def emit_mana_update(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    recipient: Any,
    current_mana: Optional[float] = None,
    max_mana: Optional[float] = None,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
    amount: Optional[float] = None,
    regen_rate: Optional[float] = None,
):
    ts = timestamp if timestamp is not None else _now_ts()
    previous_mana = getattr(recipient, 'mana', None)
    if current_mana is None:
        current_mana = previous_mana
        if current_mana is None:
            raise RuntimeError(
                f'Cannot read canonical mana state for unit={getattr(recipient, "id", None)}'
            )
    else:
        try:
            _set_and_verify_canonical_mana(recipient, current_mana)
        except Exception as exc:
            try:
                if previous_mana is not None:
                    _set_and_verify_canonical_mana(recipient, previous_mana)
            except Exception:
                pass
            raise RuntimeError(
                f'Canonical mana mutation failed for unit={getattr(recipient, "id", None)}'
            ) from exc
    if max_mana is None:
        max_mana = getattr(recipient, 'max_mana', None)

    payload = {
        'unit_id': getattr(recipient, 'id', None),
        'unit_name': getattr(recipient, 'name', None),
        'current_mana': current_mana,
        'max_mana': max_mana,
        'unit_hp': getattr(recipient, 'hp', None),  # AUTHORITATIVE: current HP
        'side': side,
        'timestamp': ts,
    }
    # include optional fields when provided (used by modular effects)
    try:
        payload['amount'] = int(amount) if amount is not None else 0
    except Exception:
        try:
            payload['amount'] = int(amount) if amount is not None else 0
        except Exception:
            payload['amount'] = 0
    try:
        if regen_rate is not None:
            payload['regen_rate'] = float(regen_rate)
    except Exception:
        pass
    _deliver_canonical_event(event_callback, 'mana_update', payload)
    return payload


def emit_mana_change(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    recipient: Any,
    amount: float,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
    include_snapshot: bool = False,
    # Optional: authoritative mana arrays for atomic updates during simulation
    mana_arrays: Optional[Dict[str, List[int]]] = None,
    unit_index: Optional[int] = None,
    unit_side: Optional[str] = None,
):
    ts = timestamp if timestamp is not None else _now_ts()

    # Death is terminal for combat state.  The frontend intentionally ignores
    # late mutations for dead units, so mutating mana here would make the
    # authoritative snapshot impossible to replay.  Keep this guard in the
    # canonical emitter as a final safety net for every caller (regen, traits,
    # scheduled attacks, and future effects).
    if getattr(recipient, '_dead', False):
        return None
    try:
        if int(getattr(recipient, 'hp', None)) <= 0:
            return None
    except (TypeError, ValueError):
        # Compatibility recipients without an HP value are allowed to use the
        # canonical mana emitter; their liveness is unknown here.
        pass

    # Apply the mana change to recipient.mana (canonical mutation).
    try:
        cur = int(getattr(recipient, 'mana', 0))
        max_m = int(getattr(recipient, 'max_mana', cur))
        requested_amount = int(amount)
        new_val = int(max(0, min(max_m, cur + requested_amount)))
    except Exception as exc:
        raise RuntimeError(
            f'Cannot prepare canonical mana mutation for unit={getattr(recipient, "id", None)}'
        ) from exc

    mana_array = None
    mana_array_previous = None
    if mana_arrays is not None:
        if not isinstance(mana_arrays, dict):
            raise TypeError('mana_arrays must be a mapping when supplied')
        if unit_side is None or unit_index is None:
            raise ValueError('unit_side and unit_index are required when mana_arrays is supplied')
        try:
            mana_array = mana_arrays[unit_side]
            mana_array_previous = mana_array[unit_index]
        except Exception as exc:
            raise RuntimeError(
                f'Cannot prepare mana mirror for unit={getattr(recipient, "id", None)} '
                f'side={unit_side} index={unit_index}'
            ) from exc

    previous_mana = getattr(recipient, 'mana', None)
    try:
        _set_and_verify_canonical_mana(recipient, new_val)

        if mana_array is not None:
            mana_array[unit_index] = new_val
            if int(mana_array[unit_index]) != new_val:
                raise RuntimeError(
                    f'Canonical mana mirror mutation did not apply for unit={getattr(recipient, "id", None)} '
                    f'side={unit_side} index={unit_index}: expected={new_val}, actual={mana_array[unit_index]}'
                )
    except Exception as exc:
        if mana_array is not None:
            try:
                mana_array[unit_index] = mana_array_previous
            except Exception:
                pass
        try:
            if previous_mana is not None:
                _set_and_verify_canonical_mana(recipient, previous_mana)
        except Exception:
            pass
        raise RuntimeError(
            f'Canonical mana mutation failed for unit={getattr(recipient, "id", None)}'
        ) from exc

    applied_amount = int(getattr(recipient, 'mana') - cur)

    # CRITICAL: Always include current_mana for UI state sync
    # EventDispatcher needs this field to determine if mana actually changed
    current_mana_value = int(getattr(recipient, 'mana'))

    payload = {
        'unit_id': getattr(recipient, 'id', None),
        'unit_name': getattr(recipient, 'name', None),
        'max_mana': int(getattr(recipient, 'max_mana', 0) or 0),
        'amount': applied_amount,
        'current_mana': current_mana_value,  # ALWAYS include, not just in snapshots
        'side': side,
        'timestamp': ts,
        'pre_mana': cur,
        'post_mana': getattr(recipient, 'mana', None),
    }
    if applied_amount > 5:
        print(f"[MANA EMIT] unit={payload.get('unit_id')} amt={applied_amount} pre={cur} post={payload.get('post_mana')} ts={ts}")
    # Back-compat: allow callers to request a snapshot-style payload
    # including authoritative HP/mana fields. Tests and callers may pass
    # include_snapshot=True to cause the emitter to attach those fields.
    # Keep this optional to avoid duplicating snapshot logic elsewhere.
    try:
        if include_snapshot:
            # if recipient has mana/hp attributes include them
            if hasattr(recipient, 'max_mana'):
                payload['max_mana'] = int(getattr(recipient, 'max_mana'))
            if hasattr(recipient, 'hp'):
                payload['unit_hp'] = int(getattr(recipient, 'hp'))
            if hasattr(recipient, 'max_hp'):
                payload['unit_max_hp'] = int(getattr(recipient, 'max_hp'))
    except Exception:
        pass

    _deliver_canonical_event(event_callback, 'mana_update', payload)
    return payload


def emit_regen_gain(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    recipient: Any,
    amount_per_sec: float,
    total_amount: Optional[float] = None,
    duration: Optional[float] = None,
    side: Optional[str] = None,
    target: Optional[str] = None,
    timestamp: Optional[float] = None,
):
    ts = timestamp if timestamp is not None else _now_ts()
    if getattr(recipient, '_dead', False):
        return None
    try:
        if int(getattr(recipient, 'hp')) <= 0:
            return None
    except (AttributeError, TypeError, ValueError):
        # Compatibility recipients without an HP value are allowed to use the
        # canonical regen emitter; their liveness is unknown here.
        pass

    try:
        previous_regen = float(getattr(recipient, 'hp_regen_per_sec', 0.0))
        expected_regen = previous_regen + float(amount_per_sec)
    except Exception as exc:
        raise RuntimeError(
            f'Cannot prepare canonical HP-regen mutation for unit={getattr(recipient, "id", None)}'
        ) from exc

    try:
        recipient.hp_regen_per_sec = expected_regen
        actual_regen = float(getattr(recipient, 'hp_regen_per_sec'))
        if actual_regen != expected_regen:
            raise RuntimeError(
                f'Canonical HP-regen mutation did not apply for unit={getattr(recipient, "id", None)}: '
                f'expected={expected_regen}, actual={actual_regen}'
            )
    except Exception as exc:
        try:
            recipient.hp_regen_per_sec = previous_regen
        except Exception:
            pass
        raise RuntimeError(
            f'Canonical HP-regen mutation failed for unit={getattr(recipient, "id", None)}'
        ) from exc

    payload = {
        'unit_id': getattr(recipient, 'id', None),
        'unit_name': getattr(recipient, 'name', None),
        'amount_per_sec': amount_per_sec,
        'total_amount': total_amount,
        'duration': duration,
        'side': side,
        'target': target,
        'timestamp': ts,
    }
    _deliver_canonical_event(event_callback, 'regen_gain', payload)
    return payload


def emit_unit_died(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    recipient: Any,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
    unit_hp: Optional[int] = None,
    # NEW: HP array references for atomic updates during death
    hp_arrays: Optional[Dict[str, List[int]]] = None,  # {'team_a': [...], 'team_b': [...]}
    unit_index: Optional[int] = None,
    unit_side: Optional[str] = None,
):
    ts = timestamp if timestamp is not None else _now_ts()
    # If already dead, avoid emitting duplicate death events
    if getattr(recipient, '_dead', False):
        return None
    # capture pre-death hp for authoritative payload (allow override)
    pre_hp = unit_hp if unit_hp is not None else getattr(recipient, 'hp', None)

    # Validate the optional simulator mirror before mutating the recipient.
    # A stale or unavailable mirror would make the death event impossible to
    # reconstruct from the authoritative HP arrays.
    hp_array = None
    hp_array_previous = None
    if hp_arrays is not None:
        if not isinstance(hp_arrays, dict):
            raise TypeError('hp_arrays must be a mapping when supplied')
        if unit_side is None or unit_index is None:
            raise ValueError('unit_side and unit_index are required when hp_arrays is supplied')
        try:
            hp_array = hp_arrays[unit_side]
            hp_array_previous = hp_array[unit_index]
        except Exception as exc:
            raise RuntimeError(
                f'Cannot prepare death HP mirror for unit={getattr(recipient, "id", None)} '
                f'side={unit_side} index={unit_index}'
            ) from exc

    previous_dead = getattr(recipient, '_dead', False)
    previous_hp = getattr(recipient, 'hp', None) if hasattr(recipient, 'hp') else None
    try:
        # Normalize in-memory HP before marking the unit dead. This ensures a
        # rejecting HP mutation cannot leave a misleading `_dead=True` state.
        if hasattr(recipient, 'hp'):
            recipient.hp = 0
            if getattr(recipient, 'hp', None) != 0:
                raise RuntimeError(
                    f'Canonical death HP mutation did not apply for unit={getattr(recipient, "id", None)}'
                )

        # NOTE: Do NOT set _death_processed here! That should only be set by
        # _process_unit_death AFTER it has processed all death-triggered effects.
        setattr(recipient, '_dead', True)

        # Update the simulator mirror only after the recipient mutation has
        # succeeded. Any failure aborts before the canonical event is emitted.
        if hp_array is not None:
            hp_array[unit_index] = 0
    except Exception:
        # Restore the pre-event state so a failed canonical transition cannot
        # leave a partially-mutated unit or HP mirror behind.
        if hp_array is not None:
            try:
                hp_array[unit_index] = hp_array_previous
            except Exception:
                pass
        try:
            setattr(recipient, '_dead', previous_dead)
        except Exception:
            pass
        if hasattr(recipient, 'hp') and previous_hp is not None:
            try:
                recipient.hp = previous_hp
            except Exception:
                pass
        raise

    payload = {
        'unit_id': getattr(recipient, 'id', None),
        'unit_name': getattr(recipient, 'name', None),
        'side': side,
        'timestamp': ts,
        # provide the authoritative pre-death HP so reconstructors can trust it
        'unit_hp': pre_hp,
        'unit_max_hp': getattr(recipient, 'max_hp', None),
    }
    _deliver_canonical_event(event_callback, 'unit_died', payload)
    return payload


def emit_unit_heal(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    target: Any,
    healer: Optional[Any],
    amount: float,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
    cause: Optional[str] = None,
    current_hp: Optional[int] = None,
):
    """Apply heal to target and emit canonical `unit_heal` event.

    Args:
        current_hp: If provided, use this as the authoritative current HP instead of reading from target.hp.
                   This is critical when HP lists are updated before calling emit_unit_heal.
    """
    ts = timestamp if timestamp is not None else _now_ts()
    # Use current_hp if provided (authoritative from hp_list), otherwise read
    # from the unit. Do not emit a unit_heal event when canonical mutation
    # fails or the recipient ignores the requested value.
    if current_hp is not None:
        cur = int(current_hp)
    else:
        cur = int(getattr(target, 'hp', 0))
    max_hp = max(0, int(getattr(target, 'max_hp', cur)))
    add = int(amount)
    new = max(0, min(max_hp, cur + add))
    _set_and_verify_canonical_hp(target, new)

    payload = {
        'healer_id': getattr(healer, 'id', None),
        'healer_name': getattr(healer, 'name', None),
        'unit_id': getattr(target, 'id', None),
        'unit_name': getattr(target, 'name', None),
        'amount': int(amount) if amount is not None else None,
        'pre_hp': cur,
        'post_hp': new,
        'unit_hp': new,  # Authoritative HP after heal
        'unit_max_hp': max_hp,
        'side': side,
        'timestamp': ts,
        'cause': cause,
    }
    # Debug logging for mrozu
    if getattr(target, 'id', None) == 'mrozu':
        import sys
        print(f"[emit_unit_heal DEBUG] payload unit_hp={payload.get('unit_hp')} pre_hp={payload.get('pre_hp')} post_hp={payload.get('post_hp')}", file=sys.stderr)
    # Do not emit unit_heal for dead units
    if getattr(target, '_dead', False):
        return None
    _deliver_canonical_event(event_callback, 'unit_heal', payload)
    return payload


def emit_hp_regen(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    recipient: Any,
    amount: float,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
    cause: Optional[str] = None,
    current_hp: Optional[int] = None,
):
    """Apply hp regen to recipient and emit canonical `hp_regen` event.

    Args:
        current_hp: If provided, use this as the authoritative current HP instead of reading from recipient.hp.
                   This is critical when HP lists are updated before calling emit_hp_regen.
    """
    ts = timestamp if timestamp is not None else _now_ts()
    # Use current_hp if provided (authoritative from hp_list), otherwise read
    # from the unit. A failed mutation is a failed combat operation, not a
    # zero-delta regen event.
    if current_hp is not None:
        cur = int(current_hp)
    else:
        cur = int(getattr(recipient, 'hp', 0))
    max_hp = max(0, int(getattr(recipient, 'max_hp', cur)))
    add = int(amount)
    new = max(0, min(max_hp, cur + add))
    _set_and_verify_canonical_hp(recipient, new)

    payload = {
        'unit_id': getattr(recipient, 'id', None),
        'unit_name': getattr(recipient, 'name', None),
        'amount': int(amount) if amount is not None else None,
        'pre_hp': cur,
        'post_hp': new,
        'unit_hp': new,  # Authoritative HP after regen
        'unit_max_hp': max_hp,
        'side': side,
        'timestamp': ts,
        'cause': cause,
    }
    # If the recipient is dead, do not emit hp_regen events for it
    if getattr(recipient, '_dead', False):
        return None
    _deliver_canonical_event(event_callback, 'hp_regen', payload)
    return payload


def emit_damage_over_time_tick(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    target: Any,
    damage: float,
    damage_type: str = 'physical',
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
    effect_id: Optional[str] = None,
    tick_index: Optional[int] = None,
    total_ticks: Optional[int] = None,
):
    ts = timestamp if timestamp is not None else _now_ts()
    # Use canonical emit_damage helper to change HP and emit a single authoritative payload
    payload = emit_damage(
        event_callback=event_callback,
        attacker=None,
        target=target,
        raw_damage=damage,
        shield_absorbed=0,
        damage_type=damage_type,
        side=side,
        timestamp=ts,
        cause='dot_tick',
        emit_event=False,
    )
    # If the target was dead, skip emitting DoT tick
    # emit_damage already called the event_callback; return canonical payload
    # Additionally emit a DoT-specific tick event so reconstructors and UI
    # can recognize the tick lifecycle (includes effect_id and authoritative HP)
    if event_callback and payload is not None:
        dot_payload = {
            'unit_id': getattr(target, 'id', None),
            'unit_name': getattr(target, 'name', None),
            'effect_id': effect_id,
            'damage': int(damage) if damage is not None else 0,
            'applied_damage': payload.get('applied_damage', int(damage) if damage is not None else 0),
            'damage_type': damage_type,
            'pre_hp': payload.get('pre_hp'),
            'post_hp': payload.get('post_hp'),
            'unit_hp': payload.get('post_hp'),
            'shield_absorbed': payload.get('shield_absorbed', 0),
            'post_shield': payload.get('post_shield'),
            'unit_shield': payload.get('unit_shield'),
            'tick_index': tick_index,
            'total_ticks': total_ticks,
            'side': side,
            'timestamp': ts,
        }
        _deliver_canonical_event(event_callback, 'damage_over_time_tick', dot_payload)

    return payload


def emit_gold_reward(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    recipient: Any,
    amount: int,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
    cause: Optional[str] = None,
):
    """Emit a canonical gold_reward event.

    Centralizes payload shape for gold rewards so downstream consumers
    (reconstructor, SSE mapping) receive a stable schema.
    """
    ts = timestamp if timestamp is not None else _now_ts()
    payload = {
        'unit_id': getattr(recipient, 'id', None),
        'unit_name': getattr(recipient, 'name', None),
        'amount': int(amount) if amount is not None else 0,
        'side': side,
        'timestamp': ts,
        'cause': cause,
    }
    _deliver_canonical_event(event_callback, 'gold_reward', payload)
    return payload


def emit_unit_stunned(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    target: Any,
    duration: float = 1.0,
    source: Optional[Any] = None,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
):
    """Apply stun flag/effect to `target` and emit canonical `unit_stunned` event."""
    ts = timestamp if timestamp is not None else _now_ts()
    if getattr(target, '_dead', False):
        return None

    try:
        previous_stunned = getattr(target, '_stunned', False)
        previous_expires_at = getattr(target, 'stunned_expires_at', None)
        previous_effects = list(getattr(target, 'effects', []) or [])
    except Exception as exc:
        raise RuntimeError(
            f'Cannot read canonical stun state for unit={getattr(target, "id", None)}'
        ) from exc

    effect_id = str(uuid.uuid4())
    expires_at = ts + float(duration) if duration and duration > 0 else None
    eff = {
        'id': effect_id,
        'type': 'stun',
        'duration': duration,
        'source': getattr(source, 'id', None) if source is not None else None,
        'expires_at': expires_at,
    }

    try:
        setattr(target, '_stunned', True)
        setattr(target, 'stunned_expires_at', expires_at)
        target.effects = previous_effects + [eff]

        if getattr(target, '_stunned', False) is not True:
            raise RuntimeError(
                f'Canonical stun flag mutation did not apply for unit={getattr(target, "id", None)}'
            )
        if getattr(target, 'stunned_expires_at', None) != expires_at:
            raise RuntimeError(
                f'Canonical stun expiry mutation did not apply for unit={getattr(target, "id", None)}'
            )
        if not any(
            isinstance(existing, dict) and existing.get('id') == effect_id
            for existing in (getattr(target, 'effects', []) or [])
        ):
            raise RuntimeError(
                f'Canonical stun effect mutation did not apply for unit={getattr(target, "id", None)} '
                f'effect_id={effect_id}'
            )
    except Exception as exc:
        try:
            setattr(target, '_stunned', previous_stunned)
        except Exception:
            pass
        try:
            setattr(target, 'stunned_expires_at', previous_expires_at)
        except Exception:
            pass
        try:
            target.effects = previous_effects
        except Exception:
            pass
        raise RuntimeError(
            f'Canonical stun mutation failed for unit={getattr(target, "id", None)}'
        ) from exc

    payload = {
        'unit_id': getattr(target, 'id', None),
        'unit_name': getattr(target, 'name', None),
        'duration': duration,
        'side': side,
        'timestamp': ts,
        'source_id': getattr(source, 'id', None) if source is not None else None,
        'effect_id': effect_id,  # CRITICAL: Include effect_id for frontend tracking
        'caster_name': getattr(source, 'name', None) if source is not None else None,
    }
    if getattr(target, '_dead', False):
        return None
    _deliver_canonical_event(event_callback, 'unit_stunned', payload)
    return payload
def emit_shield_applied(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    recipient: Any,
    amount: float,
    duration: float = 0.0,
    source: Optional[Any] = None,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
):
    """Apply shield to recipient (best-effort) and emit canonical `shield_applied` event.

    - Mutates `recipient.shield` when present (or sets it).
    - Attaches a shield effect entry to `recipient.effects`.
    - If `event_callback` is provided, calls it; otherwise returns payload for callers to forward.
    """
    ts = timestamp if timestamp is not None else _now_ts()

    # CRITICAL: Generate effect_id for ALL shield effects (same as stat_buff fix)
    effect_id = str(uuid.uuid4())

    previous_shield = getattr(recipient, 'shield', 0)
    had_effects_attr = hasattr(recipient, 'effects')
    previous_effects = list(getattr(recipient, 'effects', []) or [])

    def _rollback_partial_mutation():
        """Restore the exact pre-emission state when a partial write fails."""
        try:
            if getattr(recipient, 'shield', 0) != previous_shield:
                recipient.shield = previous_shield
        except Exception:
            # Preserve the original mutation failure; the caller still gets a
            # failed canonical emission and no event is delivered.
            pass

        try:
            if had_effects_attr:
                current_effects = list(getattr(recipient, 'effects', []) or [])
                if current_effects != previous_effects:
                    recipient.effects = list(previous_effects)
            elif hasattr(recipient, 'effects'):
                delattr(recipient, 'effects')
        except Exception:
            # Preserve the original mutation failure; the caller still gets a
            # failed canonical emission and no event is delivered.
            pass

    try:
        cur = int(previous_shield or 0)
        expected_shield = cur + int(amount)
        recipient.shield = expected_shield
        if int(getattr(recipient, 'shield', 0) or 0) != expected_shield:
            raise RuntimeError(
                f"emit_shield_applied shield postcondition failed for unit={getattr(recipient, 'id', None)}"
            )

        # Attach and verify the effect before exposing the canonical event.
        if not hasattr(recipient, 'effects') or recipient.effects is None:
            recipient.effects = []
        expires_at = ts + float(duration) if duration and duration > 0 else None
        eff = {
            'id': effect_id,  # CRITICAL: Include effect_id in effect object
            'type': 'shield',
            'amount': int(amount),
            'applied_amount': int(amount),
            'duration': duration,
            'source': getattr(source, 'id', None) if source is not None else None,
            'expires_at': expires_at,
        }
        expected_effects = list(getattr(recipient, 'effects', []) or []) + [eff]
        recipient.effects = expected_effects

        # Fail-fast invariant: active shield effect must be present on recipient.
        actual_effects = list(getattr(recipient, 'effects', []) or [])
        if actual_effects != expected_effects or not any(
            isinstance(active_effect, dict) and active_effect.get('id') == effect_id
            for active_effect in actual_effects
        ):
            raise RuntimeError(
                f"emit_shield_applied postcondition failed: missing effect_id={effect_id} on unit={getattr(recipient, 'id', None)}"
            )
    except Exception as e:
        _rollback_partial_mutation()
        raise RuntimeError(
            f"emit_shield_applied mutation failed for unit={getattr(recipient, 'id', None)} amount={amount} duration={duration}"
        ) from e

    payload = {
        'unit_id': getattr(recipient, 'id', None),
        'unit_name': getattr(recipient, 'name', None),
        'amount': int(amount) if amount is not None else None,
        'duration': duration,
        # Canonical post-state for replay. Keep unit_shield below as a
        # compatibility alias for older consumers at the boundary.
        'post_shield': getattr(recipient, 'shield', None),
        'unit_shield': getattr(recipient, 'shield', None),
        'timestamp': ts,
        'side': side,
        'source_id': getattr(source, 'id', None) if source is not None else None,
        'caster_id': getattr(source, 'id', None) if source is not None else None,
        'caster_name': getattr(source, 'name', None) if source is not None else None,
        'effect_id': effect_id,  # CRITICAL: Include effect_id for frontend tracking
    }
    if event_callback:
        event_callback('shield_applied', payload)
    return payload


def emit_damage(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    attacker: Optional[Any],
    target: Any,
    raw_damage: float,
    shield_absorbed: int = 0,
    damage_type: str = 'physical',
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
    cause: Optional[str] = None,
    emit_event: bool = True,
    bonus_attack: bool = False,
    # NEW: HP array references for atomic updates during damage
    hp_arrays: Optional[Dict[str, List[int]]] = None,  # {'team_a': [...], 'team_b': [...]}
    unit_index: Optional[int] = None,
    unit_side: Optional[str] = None,
):
    """Canonical damage emitter — centralizes HP mutation and event emission.

    Resolve incoming damage against the target's shield before HP, then emit
    authoritative `pre_hp`, `post_hp`, `shield_absorbed`, and `post_shield`.
    This function is the only allowed place to mutate the target's HP/shield
    during combat. The `shield_absorbed` argument is retained for call-site
    compatibility; absorption is derived from the target state here.
    """
    ts = timestamp if timestamp is not None else _now_ts()

    try:
        pre_hp = int(getattr(target, 'hp', None))
        max_hp = getattr(target, 'max_hp', None)
        current_shield = int(getattr(target, 'shield', 0) or 0)
    except Exception as exc:
        raise RuntimeError(
            f'Cannot read canonical damage state for unit={getattr(target, "id", None)}'
        ) from exc

    # Validate the optional simulator mirror before mutating the target. A
    # supplied mirror is part of the authoritative combat state and cannot be
    # treated as best-effort without making replay snapshots unreliable.
    hp_array = None
    hp_array_previous = None
    if hp_arrays is not None:
        if not isinstance(hp_arrays, dict):
            raise TypeError('hp_arrays must be a mapping when supplied')
        if unit_side is None or unit_index is None:
            raise ValueError('unit_side and unit_index are required when hp_arrays is supplied')
        try:
            hp_array = hp_arrays[unit_side]
            hp_array_previous = hp_array[unit_index]
        except Exception as exc:
            raise RuntimeError(
                f'Cannot prepare damage HP mirror for unit={getattr(target, "id", None)} '
                f'side={unit_side} index={unit_index}'
            ) from exc

    had_shield_attribute = hasattr(target, 'shield')
    previous_shield = current_shield

    # If target is already dead, do not apply further damage
    if getattr(target, '_dead', False):
        payload = {
            'attacker_id': getattr(attacker, 'id', None) if attacker is not None else None,
            'attacker_name': getattr(attacker, 'name', None) if attacker is not None else None,
            'attacker_current_mana': (
                int(getattr(attacker, 'mana'))
                if attacker is not None and getattr(attacker, 'mana', None) is not None
                else None
            ),
            'attacker_max_mana': (
                int(getattr(attacker, 'max_mana'))
                if attacker is not None and getattr(attacker, 'max_mana', None) is not None
                else None
            ),
            'unit_id': getattr(target, 'id', None),
            'unit_name': getattr(target, 'name', None),
            'pre_hp': pre_hp,
            'post_hp': pre_hp,
            'unit_shield': current_shield,
            'post_shield': current_shield,
            'applied_damage': 0,
            'shield_absorbed': 0,
            'damage_type': damage_type,
            'side': side,
            'timestamp': ts,
            'cause': cause,
        }
        return payload

    applied = max(0, int(raw_damage)) if raw_damage is not None else 0
    shield_absorbed = min(applied, max(0, current_shield or 0))
    damage_to_hp = applied - shield_absorbed
    post_shield = max(0, (current_shield or 0) - shield_absorbed)
    post_hp = pre_hp
    post_hp = max(0, pre_hp - damage_to_hp)
    try:
        # Mutate HP and shield only here, then verify both postconditions before
        # any canonical event can be delivered.
        _set_and_verify_canonical_hp(target, post_hp)
        target.shield = post_shield
        actual_shield = int(getattr(target, 'shield'))
        if actual_shield != post_shield:
            raise RuntimeError(
                f'Canonical shield mutation did not apply for unit={getattr(target, "id", None)}: '
                f'expected={post_shield}, actual={actual_shield}'
            )

        if hp_array is not None:
            hp_array[unit_index] = post_hp
            if int(hp_array[unit_index]) != post_hp:
                raise RuntimeError(
                    f'Canonical damage HP mirror mutation did not apply for unit={getattr(target, "id", None)} '
                    f'side={unit_side} index={unit_index}: expected={post_hp}, actual={hp_array[unit_index]}'
                )

        # Do NOT mark `_dead` or `_death_processed` here — death handling
        # (effects, rewards) should be performed by the centralized
        # effect processor via `_process_unit_death` to ensure ordering.
    except Exception as exc:
        # Restore every state component that may have been touched before the
        # failure. Rollback is best-effort because a broken recipient may also
        # reject restoration, but the operation always re-raises and never
        # publishes a success-looking event.
        if hp_array is not None:
            try:
                hp_array[unit_index] = hp_array_previous
            except Exception:
                pass
        try:
            target.shield = previous_shield
        except Exception:
            pass
        try:
            target.hp = pre_hp
        except Exception:
            pass
        if not had_shield_attribute:
            try:
                delattr(target, 'shield')
            except Exception:
                pass
        raise RuntimeError(
            f'Canonical damage mutation failed for unit={getattr(target, "id", None)}'
        ) from exc

    payload = {
        'attacker_id': getattr(attacker, 'id', None) if attacker is not None else None,
        'attacker_name': getattr(attacker, 'name', None) if attacker is not None else None,
        'attacker_current_mana': (
            int(getattr(attacker, 'mana'))
            if attacker is not None and getattr(attacker, 'mana', None) is not None
            else None
        ),
        'attacker_max_mana': (
            int(getattr(attacker, 'max_mana'))
            if attacker is not None and getattr(attacker, 'max_mana', None) is not None
            else None
        ),
        'unit_id': getattr(target, 'id', None),
        'unit_name': getattr(target, 'name', None),
        # Backwards-compatible target keys
        'target_id': getattr(target, 'id', None),
        'target_name': getattr(target, 'name', None),
        'pre_hp': pre_hp,
        'post_hp': post_hp,
        'applied_damage': applied,
        # Backwards-compatible fields expected by older reconstructor logic
        'damage': applied,
        'target_hp': post_hp,
        'new_hp': post_hp,
        'unit_hp': post_hp,
        'unit_shield': post_shield,
        'post_shield': post_shield,
        'shield_absorbed': shield_absorbed,
        'damage_type': damage_type,
        'side': side,
        'timestamp': ts,
        'cause': cause,
        'bonus_attack': bonus_attack,
    }

    if emit_event and event_callback:
        # Emit modern canonical event name. Delivery failures must abort the
        # current combat rather than returning a result with a missing event.
        _deliver_canonical_event(event_callback, 'unit_attack', payload)

    # If target died as the result, also emit unit_died with authoritative pre_hp
    # ONLY emit if event_callback is provided (otherwise caller will handle death manually)
    if post_hp == 0 and event_callback is not None:
        emit_unit_died(event_callback, target, side=side, timestamp=ts, unit_hp=pre_hp)

    return payload


def emit_effect_expired(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    target: Any,
    effect_id: str,
    unit_hp: Optional[int] = None,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
    effect_type: Optional[str] = None,
    stat: Optional[str] = None,
    applied_delta: Optional[int] = None,
    applied_amount: Optional[int] = None,
):
    """Emit an `effect_expired` event describing an expired effect on a unit.

    This function MUST raise exceptions on invalid inputs so callers can
    detect problems early (no silent fallbacks).
    """
    effect_id = _require_non_empty_effect_id(effect_id, 'effect_expired')
    ts = timestamp if timestamp is not None else _now_ts()

    payload = {
        'unit_id': getattr(target, 'id', None),
        'unit_name': getattr(target, 'name', None),
        'effect_id': effect_id,
        'post_hp': unit_hp if unit_hp is not None else getattr(target, 'hp', None),
        'unit_hp': unit_hp if unit_hp is not None else getattr(target, 'hp', None),
        'side': side,
        'timestamp': ts,
    }
    # Expiration happens after the backend mutates the unit. Serialize the
    # resulting value so replay never has to re-implement reversion math.
    if stat:
        post_value = getattr(target, stat, None)
        if post_value is not None:
            payload[f'post_{stat}'] = post_value
    if effect_type == 'shield':
        payload['post_shield'] = getattr(target, 'shield', None)
    if effect_type is not None:
        payload['effect_type'] = effect_type
    if stat is not None:
        payload['stat'] = stat
    if applied_delta is not None:
        payload['applied_delta'] = applied_delta
    if applied_amount is not None:
        payload['applied_amount'] = applied_amount

    # Do not swallow errors — let them propagate to the caller for visibility
    if event_callback:
        event_callback('effect_expired', payload)

    return payload


def emit_damage_over_time_expired(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    target: Any,
    effect_id: str,
    unit_hp: Optional[int] = None,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
):
    """Emit a `damage_over_time_expired` event when a DoT effect finishes.

    This function intentionally raises on unexpected failures so test
    harnesses and callers surface errors immediately.
    """
    effect_id = _require_non_empty_effect_id(effect_id, 'damage_over_time_expired')
    ts = timestamp if timestamp is not None else _now_ts()

    payload = {
        'unit_id': getattr(target, 'id', None),
        'unit_name': getattr(target, 'name', None),
        'effect_id': effect_id,
        'post_hp': unit_hp if unit_hp is not None else getattr(target, 'hp', None),
        'unit_hp': unit_hp if unit_hp is not None else getattr(target, 'hp', None),
        'side': side,
        'timestamp': ts,
    }

    if event_callback:
        event_callback('damage_over_time_expired', payload)

    return payload
