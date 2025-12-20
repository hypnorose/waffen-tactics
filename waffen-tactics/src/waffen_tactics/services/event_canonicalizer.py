import time as _time
import uuid
from typing import Optional, Dict, Any, Callable


def _now_ts():
    return _time.time()


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

    effect_id = None

    # Apply immediate numeric mutation when appropriate
    delta = None
    try:
        if stat in ('attack', 'defense'):
            if value_type == 'percentage':
                delta = int(getattr(recipient, stat, 0) * (float(value) / 100.0))
            else:
                delta = int(value)
            if permanent:
                setattr(recipient, stat, getattr(recipient, stat, 0) + delta)
            else:
                # For temporary buffs with no handler system, we still apply immediate numeric change
                setattr(recipient, stat, getattr(recipient, stat, 0) + delta)
        elif stat == 'hp':
            # delegate hp changes to emit_heal for canonical emission
            delta = int(value)
            try:
                emit_heal(event_callback, recipient, delta, source=source, side=side, timestamp=ts)
            except Exception:
                # best-effort fallback
                recipient.hp = min(getattr(recipient, 'max_hp', getattr(recipient, 'hp', 0)), getattr(recipient, 'hp', 0) + delta)
        elif stat in ('attack_speed', 'lifesteal', 'damage_reduction', 'hp_regen_per_sec'):
            # float fields
            cur = float(getattr(recipient, stat, 0.0))
            if value_type == 'percentage' and stat == 'attack_speed':
                delta = cur * (float(value) / 100.0)
            else:
                delta = float(value)
            setattr(recipient, stat, cur + delta)
        # other stats are stored as-is in effects and may be applied by UI recompute
    except Exception:
        # Best-effort mutation; don't break emitter on unexpected recipient shapes
        pass

    # Attach effect entry if duration provided or if permanent flag indicates persistent buff
    if duration is not None or permanent:
        effect_id = str(uuid.uuid4())
        effect = {
            'id': effect_id,
            'type': 'buff' if (value is None or value >= 0) else 'debuff',
            'stat': stat,
            'value': value,
            'value_type': value_type,
            'duration': duration,
            'permanent': permanent,
            'source': getattr(source, 'id', None) if source is not None else None,
            'expires_at': (ts + duration) if (duration and duration > 0) else None,
        }
        recipient.effects = list(getattr(recipient, 'effects', [])) + [effect]

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

    if event_callback:
        try:
            print(f"[EMIT_STAT_BUFF] calling callback for recipient={getattr(recipient,'id',None)}")
            event_callback('stat_buff', payload)
            print(f"[EMIT_STAT_BUFF] callback returned for recipient={getattr(recipient,'id',None)}")
        except Exception:
            # Don't let event emission break simulation
            print(f"[EMIT_STAT_BUFF] callback raised for recipient={getattr(recipient,'id',None)}")
            pass

    return payload


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
    try:
        # Use current_hp if provided (authoritative from hp_list), otherwise read from unit
        if current_hp is not None:
            cur = int(current_hp)
        else:
            cur = int(getattr(recipient, 'hp', 0))
        max_hp = int(getattr(recipient, 'max_hp', cur))
        add = int(amount)
        new = min(max_hp, cur + add)
        # apply mutation to both recipient.hp and return new value
        recipient.hp = new
    except Exception:
        # best-effort
        new = getattr(recipient, 'hp', None)
        max_hp = getattr(recipient, 'max_hp', None)
        if current_hp is not None:
            cur = current_hp
        else:
            cur = getattr(recipient, 'hp', None)

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
    if event_callback:
        try:
            event_callback('heal', payload)
        except Exception:
            pass
    return payload


def emit_mana_update(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    recipient: Any,
    current_mana: Optional[float] = None,
    max_mana: Optional[float] = None,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
):
    ts = timestamp if timestamp is not None else _now_ts()
    try:
        if current_mana is None:
            current_mana = getattr(recipient, 'mana', None)
        else:
            recipient.mana = current_mana
        if max_mana is None:
            max_mana = getattr(recipient, 'max_mana', None)
    except Exception:
        pass

    payload = {
        'unit_id': getattr(recipient, 'id', None),
        'unit_name': getattr(recipient, 'name', None),
        'current_mana': current_mana,
        'max_mana': max_mana,
        'side': side,
        'timestamp': ts,
    }
    if event_callback:
        try:
            event_callback('mana_update', payload)
        except Exception:
            pass
    return payload


def emit_mana_change(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    recipient: Any,
    amount: float,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
):
    ts = timestamp if timestamp is not None else _now_ts()
    # Note: mana change should be applied by caller, this just emits the event

    payload = {
        'unit_id': getattr(recipient, 'id', None),
        'unit_name': getattr(recipient, 'name', None),
        'amount': int(amount) if amount is not None else None,
        'side': side,
        'timestamp': ts,
    }
    if event_callback:
        try:
            event_callback('mana_update', payload)
        except Exception:
            pass
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
    try:
        cur = float(getattr(recipient, 'hp_regen_per_sec', 0.0))
        recipient.hp_regen_per_sec = cur + float(amount_per_sec)
    except Exception:
        pass

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
    if event_callback:
        try:
            event_callback('regen_gain', payload)
        except Exception:
            pass
    return payload


def emit_unit_died(
    event_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    recipient: Any,
    side: Optional[str] = None,
    timestamp: Optional[float] = None,
    unit_hp: Optional[int] = None,
):
    ts = timestamp if timestamp is not None else _now_ts()
    # If already dead, avoid emitting duplicate death events
    if getattr(recipient, '_dead', False):
        return None
    # capture pre-death hp for authoritative payload (allow override)
    pre_hp = unit_hp if unit_hp is not None else getattr(recipient, 'hp', None)
    try:
        # mark dead and normalize in-memory hp immediately so authoritative
        # state used by snapshots is consistent when this event is emitted
        setattr(recipient, '_dead', True)
        # NOTE: Do NOT set _death_processed here! That should only be set by
        # _process_unit_death AFTER it has processed all death-triggered effects.
        if hasattr(recipient, 'hp'):
            # enforce HP changes only via canonical helpers
            recipient.hp = 0
    except Exception:
        pass

    payload = {
        'unit_id': getattr(recipient, 'id', None),
        'unit_name': getattr(recipient, 'name', None),
        'side': side,
        'timestamp': ts,
        # provide the authoritative pre-death HP so reconstructors can trust it
        'unit_hp': pre_hp,
        'unit_max_hp': getattr(recipient, 'max_hp', None),
    }
    if event_callback:
        try:
            event_callback('unit_died', payload)
        except Exception:
            pass
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
    # apply heal to target
    try:
        # Use current_hp if provided (authoritative from hp_list), otherwise read from unit
        if current_hp is not None:
            cur = int(current_hp)
        else:
            cur = int(getattr(target, 'hp', 0))
        max_hp = int(getattr(target, 'max_hp', cur))
        add = int(amount)
        new = min(max_hp, cur + add)
        # Debug logging for mrozu
        if getattr(target, 'id', None) == 'mrozu':
            import sys
            print(f"[emit_unit_heal DEBUG] target={target.id} current_hp={current_hp} cur={cur} amount={amount} add={add} max_hp={max_hp} new={new}", file=sys.stderr)
        target.hp = new
    except Exception:
        new = getattr(target, 'hp', None)
        max_hp = getattr(target, 'max_hp', None)
        if current_hp is not None:
            cur = current_hp
        else:
            cur = getattr(target, 'hp', None)

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
    if event_callback:
        try:
            event_callback('unit_heal', payload)
        except Exception:
            pass
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
        try:
            dot_payload = {
                'unit_id': getattr(target, 'id', None),
                'unit_name': getattr(target, 'name', None),
                'effect_id': effect_id,
                'damage': int(damage) if damage is not None else 0,
                'damage_type': damage_type,
                'unit_hp': payload.get('post_hp'),
                'tick_index': tick_index,
                'total_ticks': total_ticks,
                'side': side,
                'timestamp': ts,
            }
            event_callback('damage_over_time_tick', dot_payload)
        except Exception:
            pass

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
    if event_callback:
        try:
            event_callback('gold_reward', payload)
        except Exception:
            pass
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
    try:
        # Mark stun state and expiry
        expires_at = ts + float(duration) if duration and duration > 0 else None
        setattr(target, '_stunned', True)
        setattr(target, 'stunned_expires_at', expires_at)
        # attach effect object for client recompute
        if not hasattr(target, 'effects') or target.effects is None:
            target.effects = []
        eff = {
            'type': 'stun',
            'duration': duration,
            'source': getattr(source, 'id', None) if source is not None else None,
            'expires_at': expires_at,
        }
        target.effects = list(getattr(target, 'effects', [])) + [eff]
    except Exception:
        pass

    payload = {
        'unit_id': getattr(target, 'id', None),
        'unit_name': getattr(target, 'name', None),
        'duration': duration,
        'side': side,
        'timestamp': ts,
        'source_id': getattr(source, 'id', None) if source is not None else None,
    }
    if getattr(target, '_dead', False):
        return None
    if event_callback:
        try:
            event_callback('unit_stunned', payload)
        except Exception:
            pass
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
    try:
        cur = int(getattr(recipient, 'shield', 0) or 0)
        recipient.shield = cur + int(amount)
        # attach effect
        if not hasattr(recipient, 'effects') or recipient.effects is None:
            recipient.effects = []
        expires_at = ts + float(duration) if duration and duration > 0 else None
        eff = {
            'type': 'shield',
            'amount': int(amount),
            'duration': duration,
            'source': getattr(source, 'id', None) if source is not None else None,
            'expires_at': expires_at,
        }
        recipient.effects = list(getattr(recipient, 'effects', [])) + [eff]
    except Exception:
        expires_at = ts + float(duration) if duration and duration > 0 else None

    payload = {
        'unit_id': getattr(recipient, 'id', None),
        'unit_name': getattr(recipient, 'name', None),
        'amount': int(amount) if amount is not None else None,
        'duration': duration,
        'unit_shield': getattr(recipient, 'shield', None),
        'timestamp': ts,
        'side': side,
        'source_id': getattr(source, 'id', None) if source is not None else None,
        'caster_id': getattr(source, 'id', None) if source is not None else None,
        'caster_name': getattr(source, 'name', None) if source is not None else None,
    }
    if event_callback:
        try:
            event_callback('shield_applied', payload)
        except Exception:
            pass
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
):
    """Canonical damage emitter — centralizes HP mutation and event emission.

    Always emits an authoritative damage payload containing `pre_hp` and `post_hp`.
    This function is the only allowed place to mutate `target.hp`.
    """
    ts = timestamp if timestamp is not None else _now_ts()

    pre_hp = None
    max_hp = None
    try:
        pre_hp = int(getattr(target, 'hp', None))
        max_hp = getattr(target, 'max_hp', None)
    except Exception:
        pass

    # If target is already dead, do not apply further damage
    if getattr(target, '_dead', False):
        payload = {
            'attacker_id': getattr(attacker, 'id', None) if attacker is not None else None,
            'attacker_name': getattr(attacker, 'name', None) if attacker is not None else None,
            'unit_id': getattr(target, 'id', None),
            'unit_name': getattr(target, 'name', None),
            'pre_hp': pre_hp,
            'post_hp': pre_hp,
            'applied_damage': 0,
            'shield_absorbed': shield_absorbed,
            'damage_type': damage_type,
            'side': side,
            'timestamp': ts,
            'cause': cause,
        }
        return payload

    applied = int(raw_damage) if raw_damage is not None else 0
    post_hp = pre_hp
    try:
        post_hp = max(0, (pre_hp or 0) - applied)
        # Mutate HP only here
        target.hp = post_hp
        # Do NOT mark `_dead` or `_death_processed` here — death handling
        # (effects, rewards) should be performed by the centralized
        # effect processor via `_process_unit_death` to ensure ordering.
    except Exception:
        pass

    payload = {
        'attacker_id': getattr(attacker, 'id', None) if attacker is not None else None,
        'attacker_name': getattr(attacker, 'name', None) if attacker is not None else None,
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
        'shield_absorbed': shield_absorbed,
        'damage_type': damage_type,
        'side': side,
        'timestamp': ts,
        'cause': cause,
    }

    if emit_event and event_callback:
        try:
            event_callback('attack', payload)
        except Exception:
            pass

    # If target died as the result, also emit unit_died with authoritative pre_hp
    if post_hp == 0:
        try:
            emit_unit_died(event_callback, target, side=side, timestamp=ts, unit_hp=pre_hp)
        except Exception:
            pass

    return payload
