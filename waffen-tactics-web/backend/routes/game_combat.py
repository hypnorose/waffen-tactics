"""
Game combat - handlers for combat system and SSE streaming
"""
from flask import request, jsonify, Response, stream_with_context
import time
import json
import hashlib
import math
from pathlib import Path
import logging
from waffen_tactics.services.database import (
    DatabaseManager,
    PlayerActionConflictError,
    InvalidStoredPlayerStateError,
)
from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.services.economy import apply_post_combat_rewards
from services.combat_service import (
    prepare_player_units_for_combat, prepare_opponent_units_for_combat,
    prepare_round_buffs, run_combat_simulation, process_combat_results, resolve_defeat_hp_mutation,
    resolve_persisted_team_units,
)
from waffen_tactics.services.combat_errors import (
    CombatError,
    CombatExecutionError,
    InvalidCombatInputError,
)
from .game_state_utils import run_async, enrich_player_state
from routes.auth import verify_token
# Initialize services
DB_PATH = str(Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'waffen_tactics_game.db')
db_manager = DatabaseManager(DB_PATH)
logger = logging.getLogger('waffen_tactics.game_combat')
game_manager = GameManager()

# SSE framing is retained for compatibility with the current fetch parser;
# the delivery model is a committed batch/replay, not a live event stream.
COMBAT_DELIVERY_MODE = 'batch_replay'


def _combat_response_headers():
    return {
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'X-Combat-Delivery-Mode': COMBAT_DELIVERY_MODE,
        'X-Combat-Live-Stream': 'false',
    }


def _require_effect_id(data: dict, event_type: str):
    """Require the canonical non-empty string effect identity at the SSE boundary."""
    effect_id = data.get('effect_id')
    if not isinstance(effect_id, str) or not effect_id.strip():
        raise RuntimeError(
            f"{event_type} missing required effect_id at seq={data.get('seq')}"
        )
    return effect_id


def map_event_to_sse_payload(event_type: str, data: dict):
    """Map internal combat events to SSE payload dicts.

    Exposed at module level so tests can call it directly to verify the
    JSON payloads the route would stream.
    """
    logger.debug(f"Mapping event {event_type} with seq={data.get('seq')}")
    # Support both legacy 'attack' and new 'unit_attack' event types
    res = None
    if event_type in ('attack', 'unit_attack'):
        post_shield = data.get('post_shield')
        if post_shield is None:
            # Compatibility alias is accepted only at the transport boundary.
            post_shield = data.get('unit_shield')
        if data.get('shield_absorbed', 0) and post_shield is None:
            raise RuntimeError(
                f"unit_attack with shield absorption missing canonical post_shield at seq={data.get('seq')} "
                f"payload_keys={sorted(list(data.keys()))}"
            )
        res = {
            'type': 'unit_attack',
            'attacker_id': data.get('attacker_id'),
            'attacker_name': data.get('attacker_name'),
            'attacker_current_mana': data.get('attacker_current_mana'),
            'attacker_max_mana': data.get('attacker_max_mana'),
            'target_id': data.get('target_id'),
            'target_name': data.get('target_name'),
            # Backwards-compatible aliases: some consumers expect `unit_name`
            # and `applied_damage` keys. Preserve authoritative values by
            # preferring the explicit fields when provided.
            # Prefer `target_name` when present (authoritative), fall back
            # to `unit_name` for legacy payloads.
            'unit_name': data.get('target_name', data.get('unit_name')),
            'damage': data.get('damage'),
            'applied_damage': data.get('applied_damage', data.get('damage')),
            'shield_absorbed': data.get('shield_absorbed', 0),
            'post_shield': post_shield,
            'unit_shield': data.get('unit_shield', post_shield),
            'bonus_attack': data.get('bonus_attack', False),
            # Do NOT silently fallback to `unit_hp` here — preserve the
            # canonical `target_hp` value as provided by the backend.
            # If `target_hp` is missing, let that be visible to callers/tests
            # so we can surface bugs instead of hiding them.
            'target_hp': data.get('target_hp'),
            'target_max_hp': data.get('target_max_hp'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'unit_died':
        res = {
            'type': 'unit_died',
            'unit_id': data['unit_id'],
            'unit_name': data['unit_name'],
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'regen_gain':
        post_regen = data.get('post_hp_regen_per_sec')
        if isinstance(post_regen, bool) or not isinstance(post_regen, (int, float)) or not math.isfinite(float(post_regen)):
            raise RuntimeError(
                f"regen_gain missing required post_hp_regen_per_sec at seq={data.get('seq')} "
                f"payload_keys={sorted(list(data.keys()))}"
            )
        res = {
            'type': 'regen_gain',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'amount_per_sec': data.get('amount_per_sec'),
            'total_amount': data.get('total_amount'),
            'duration': data.get('duration'),
            'post_hp_regen_per_sec': post_regen,
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type in ('heal', 'unit_heal'):
        if data.get('post_hp') is None:
            raise RuntimeError(
                f"{event_type} missing required post_hp at seq={data.get('seq')} payload_keys={sorted(list(data.keys()))}"
            )
        res = {
            'type': 'unit_heal',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'amount': data.get('amount'),
            'healer_id': data.get('healer_id') or data.get('caster_id'),
            'healer_name': data.get('healer_name') or data.get('caster_name'),
            'pre_hp': data.get('pre_hp'),
            'post_hp': data.get('post_hp'),
            'unit_hp': data.get('unit_hp'),
            'unit_max_hp': data.get('unit_max_hp') or data.get('max_hp'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'gold_reward':
        amt = int(data.get('amount', 0) or 0)
        res = {
            'type': 'gold_reward',
            'amount': amt,
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'side': data.get('side'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'stat_buff':
        effect_id = _require_effect_id(data, event_type)
        if data.get('applied_delta') is None:
            raise RuntimeError(
                f"stat_buff missing required applied_delta at seq={data.get('seq')} payload_keys={sorted(list(data.keys()))}"
            )
        # Build an effect summary so the UI can show badges on unit cards
        eff = {
            'type': data.get('buff_type', 'buff'),
            'id': effect_id,
            'stat': data.get('stat'),
            'amount': data.get('amount') or data.get('value'),
            'value_type': data.get('value_type'),
            'duration': data.get('duration')
        }
        res = {
            'type': 'stat_buff',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'caster_id': data.get('caster_id'),
            'caster_name': data.get('caster_name'),
            'stat': data.get('stat'),
            'amount': data.get('amount') or data.get('value'),
            'buff_type': data.get('buff_type', 'buff'),
            'duration': data.get('duration'),
            'applied_delta': data.get('applied_delta'),
            'side': data.get('side'),
            'effect': eff,
            'effect_id': effect_id,
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'mana_update':
        # Build payload carefully - only include fields that are present and not None
        res = {
            'type': 'mana_update',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'amount': data.get('amount'),
            'current_mana': data.get('current_mana'),  # CRITICAL: Pass authoritative mana value to UI
            'side': data.get('side'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
        # CRITICAL: Only include unit_hp/max_mana if they are present AND not None
        # Sending null values would erase UI state!
        if data.get('max_mana') is not None:
            res['max_mana'] = data.get('max_mana')
        if data.get('unit_hp') is not None:
            res['unit_hp'] = data.get('unit_hp')
    if event_type == 'skill_cast':
        # Legacy compatibility only. The live ruleset is attack-only, but we
        # still map older replay payloads that may contain skill_cast.
        res = {
            'type': 'skill_cast',
            'caster_id': data.get('caster_id'),
            'caster_name': data.get('caster_name'),
            'skill_name': data.get('skill_name'),
            'target_id': data.get('target_id'),
            'target_name': data.get('target_name'),
            'damage': data.get('damage'),
            'target_hp': data.get('target_hp'),
            'target_max_hp': data.get('target_max_hp'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'passive_triggered':
        res = {
            'type': 'passive_triggered',
            'passive_id': data.get('passive_id'),
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'description': data.get('description'),
            'trigger': data.get('trigger'),
            'effect': data.get('effect'),
            'target_id': data.get('target_id'),
            'preference': data.get('preference'),
            'side': data.get('side'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'effect_applied':
        if not data.get('unit_id'):
            raise RuntimeError(
                f"effect_applied missing required unit_id at seq={data.get('seq')}"
            )
        effect = data.get('effect')
        if not isinstance(effect, dict):
            raise RuntimeError(
                f"effect_applied missing canonical effect object at seq={data.get('seq')}"
            )
        effect_id = _require_effect_id(data, event_type)
        embedded_effect_id = effect.get('id')
        if not isinstance(embedded_effect_id, str) or not embedded_effect_id.strip():
            raise RuntimeError(
                f"effect_applied missing canonical effect.id at seq={data.get('seq')}"
            )
        if embedded_effect_id != effect_id:
            raise RuntimeError(
                f"effect_applied effect identity mismatch at seq={data.get('seq')}"
            )
        if not isinstance(effect.get('type'), str) or not effect.get('type').strip():
            raise RuntimeError(
                f"effect_applied missing canonical effect.type at seq={data.get('seq')}"
            )
        res = {
            'type': 'effect_applied',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'effect_id': effect_id,
            'effect_type': data.get('effect_type') or effect.get('type'),
            'effect': effect,
            'source_id': data.get('source_id') or effect.get('source'),
            'caster_id': data.get('caster_id') or effect.get('source'),
            'caster_name': data.get('caster_name'),
            'side': data.get('side'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'shield_applied':
        effect_id = _require_effect_id(data, event_type)
        post_shield = data.get('post_shield')
        if post_shield is None:
            # Accept the pre-contract emitter alias only at this boundary;
            # downstream replay receives the canonical name below.
            post_shield = data.get('unit_shield')
        if post_shield is None:
            raise RuntimeError(
                f"shield_applied missing required post_shield at seq={data.get('seq')} "
                f"payload_keys={sorted(list(data.keys()))}"
            )
        eff = {
            'type': 'shield',
            'amount': data.get('amount'),
            'duration': data.get('duration')
        }
        res = {
            'type': 'shield_applied',
            'unit_id': data.get('unit_id'),
            'caster_id': data.get('caster_id'),
            'caster_name': data.get('caster_name'),
            'unit_name': data.get('unit_name'),
            'amount': data.get('amount'),
            'duration': data.get('duration'),
            'post_shield': post_shield,
            'unit_shield': post_shield,
            'effect': eff,
            'effect_id': effect_id,
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    # DEBUG: Print mapped unit_attack payloads so we can see exactly what
    # is streamed over SSE (helps debug UI not applying events).
    try:
        if res and res.get('type') == 'unit_attack':
            try:
                print(f"[SSE_MAPPED_PAYLOAD] type=unit_attack seq={res.get('seq')} attacker={res.get('attacker_id')} target={res.get('target_id')} payload_keys={list(res.keys())}")
            except Exception:
                print("[SSE_MAPPED_PAYLOAD] unit_attack mapped (unable to stringify payload)")
    except Exception:
        pass
    try:
        if res and res.get('type') == 'animation_start':
            try:
                print(f"[SSE_MAPPED_PAYLOAD] type=animation_start seq={res.get('seq')} animation_id={res.get('animation_id')} attacker={res.get('attacker_id')} target={res.get('target_id')} duration={res.get('duration')}")
            except Exception:
                print("[SSE_MAPPED_PAYLOAD] animation_start mapped (unable to stringify payload)")
    except Exception:
        pass
    if event_type == 'unit_stunned':
        effect_id = _require_effect_id(data, event_type)
        eff = {'type': 'stun', 'duration': data.get('duration')}
        res = {
            'type': 'unit_stunned',
            'unit_id': data.get('unit_id'),
            'caster_id': data.get('caster_id'),
            'unit_name': data.get('unit_name'),
            'caster_name': data.get('caster_name'),
            'duration': data.get('duration'),
            'effect': eff,
            'effect_id': effect_id,
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'damage_over_time_applied':
        damage = data.get('damage')
        if not data.get('unit_id'):
            raise RuntimeError(
                f"damage_over_time_applied missing required unit_id at seq={data.get('seq')}"
            )
        effect_id = _require_effect_id(data, event_type)
        if not isinstance(damage, (int, float)) or isinstance(damage, bool) or not math.isfinite(damage) or damage <= 0:
            raise RuntimeError(
                f"damage_over_time_applied missing canonical damage at seq={data.get('seq')}"
            )
        if data.get('expires_at') is None:
            raise RuntimeError(
                f"damage_over_time_applied missing canonical expires_at at seq={data.get('seq')}"
            )
        eff = {
            'type': 'damage_over_time',
            'damage': damage,
            'damage_type': data.get('damage_type'),
            'duration': data.get('duration'),
            'interval': data.get('interval'),
            'ticks': data.get('ticks'),
            'id': effect_id,
            'next_tick_time': data.get('next_tick_time'),
            'expires_at': data.get('expires_at'),
            'source': data.get('source'),
        }
        res = {
            'type': 'damage_over_time_applied',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'caster_id': data.get('caster_id'),
            'caster_name': data.get('caster_name'),
            'damage': damage,
            'damage_type': data.get('damage_type'),
            'duration': data.get('duration'),
            'interval': data.get('interval'),
            'ticks': data.get('ticks'),
            'effect': eff,
            'effect_id': effect_id,
            'next_tick_time': data.get('next_tick_time'),
            'expires_at': data.get('expires_at'),
            'source': data.get('source'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'damage_over_time_tick':
        effect_id = _require_effect_id(data, event_type)
        post_shield = data.get('post_shield')
        if post_shield is None:
            # Compatibility alias is accepted only at the transport boundary.
            post_shield = data.get('unit_shield')
        shield_absorbed = data.get('shield_absorbed', 0)
        if shield_absorbed and post_shield is None:
            raise RuntimeError(
                f"damage_over_time_tick with shield absorption missing canonical post_shield at seq={data.get('seq')} "
                f"payload_keys={sorted(list(data.keys()))}"
            )
        eff = {
            'type': 'damage_over_time',
            'damage': data.get('damage'),
            'damage_type': data.get('damage_type'),
            'id': effect_id,
        }
        res = {
            'type': 'damage_over_time_tick',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'damage': data.get('damage'),
            'damage_type': data.get('damage_type'),
            'pre_hp': data.get('pre_hp'),
            'post_hp': data.get('post_hp'),
            'unit_hp': data.get('unit_hp'),
            'unit_max_hp': data.get('unit_max_hp'),
            'shield_absorbed': shield_absorbed,
            'post_shield': post_shield,
            'unit_shield': data.get('unit_shield', post_shield),
            'side': data.get('side'),
            'effect': eff,
            'effect_id': effect_id,
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'damage_over_time_expired':
        # Explicit expire event for DoT effects — include effect id and
        # authoritative unit HP so reconstructors can remove the effect
        # exactly when the server considers it expired.
        effect_id = _require_effect_id(data, event_type)
        res = {
            'type': 'damage_over_time_expired',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'effect_id': effect_id,
            'pre_hp': data.get('pre_hp'),
            'post_hp': data.get('post_hp'),
            'unit_hp': data.get('unit_hp'),
            'side': data.get('side'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'effect_expired':
        effect_id = _require_effect_id(data, event_type)
        res = {
            'type': 'effect_expired',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'effect_id': effect_id,
            'pre_hp': data.get('pre_hp'),
            'post_hp': data.get('post_hp'),
            'unit_hp': data.get('unit_hp'),
            'effect_type': data.get('effect_type'),
            'stat': data.get('stat'),
            'post_max_hp': data.get('post_max_hp'),
            'post_attack': data.get('post_attack'),
            'post_defense': data.get('post_defense'),
            'post_attack_speed': data.get('post_attack_speed'),
            'post_shield': data.get('post_shield'),
            'applied_delta': data.get('applied_delta'),
            'applied_amount': data.get('applied_amount'),
            'side': data.get('side'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'hp_regen':
        res = {
            'type': 'hp_regen',
            'unit_id': data.get('unit_id'),
            'unit_name': data.get('unit_name'),
            'amount': data.get('amount'),
            'pre_hp': data.get('pre_hp'),
            'post_hp': data.get('post_hp'),
            'unit_hp': data.get('unit_hp'),  # Authoritative HP after regen
            'unit_max_hp': data.get('unit_max_hp'),
            'side': data.get('side'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'state_snapshot':
        res = {
            'type': 'state_snapshot',
            'player_units': data.get('player_units'),
            'opponent_units': data.get('opponent_units'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }
    if event_type == 'animation_start':
        res = {
            'type': 'animation_start',
            'animation_id': data.get('animation_id'),
            'attacker_id': data.get('attacker_id'),
            'target_id': data.get('target_id'),
            'duration': data.get('duration'),
            'timestamp': data.get('timestamp', time.time()),
            'seq': data.get('seq')
        }

    # Attach seq and event_id centrally so every SSE payload carries them when available
    if res is not None:
        # Prefer existing seq on the mapped payload, but fall back to provided data
        if 'seq' not in res or res.get('seq') is None:
            if 'seq' in data:
                res['seq'] = data.get('seq')
        # Attach event_id if present
        if 'event_id' in data and data.get('event_id'):
            res['event_id'] = data.get('event_id')
        # Attach game_state if present. Make a snapshot copy so payloads are
        # independent of later simulator mutations. Allow exceptions to
        # propagate so caller can observe issues rather than silently falling back.
        if 'game_state' in data:
            import copy
            res['game_state'] = copy.deepcopy(data['game_state'])
        logger.debug(f"Mapped {event_type} to payload with seq={res.get('seq')}")
        return res

    return None


def combat_error_sse_payload(error: CombatError) -> dict:
    """Return the stable client contract for a failed combat request."""
    return {
        'type': 'error',
        'code': error.code,
        'retriable': error.retriable,
        'message': error.safe_message,
    }


def start_combat():
    """Run committed combat and return an SSE-framed batch for replay."""

    # The combat contract requires a JSON object because token and
    # idempotency_key are named fields.  Reject other JSON shapes at the
    # request boundary instead of allowing `.get()` to raise AttributeError.
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        logger.warning('start_combat: missing or invalid JSON object from %s', request.remote_addr)
        return jsonify({'error': 'Missing token'}), 401

    # Get token from request body (POST)
    token = data.get('token', '')
    if not token:
        logger.warning('start_combat: missing token in request from %s', request.remote_addr)
        return jsonify({'error': 'Missing token'}), 401

    try:
        payload = verify_token(token)
        user_id = int(payload['user_id'])
    except Exception as e:
        logger.warning('start_combat: invalid token: %s', str(e))
        return jsonify({'error': 'Invalid token'}), 401

    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'Player not found'}), 404

    # Combat is retryable. Prefer the client key; otherwise derive one from
    # the authoritative starting round so duplicate submissions of the same
    # round share one durable action boundary.
    idempotency_key = request.headers.get('Idempotency-Key') or data.get('idempotency_key')
    idempotency_key = str(idempotency_key).strip() if idempotency_key else ''
    if not idempotency_key:
        idempotency_key = f"combat:{user_id}:{player.round_number}"
    combat_result_id = hashlib.sha256(
        f"combat:{user_id}:{idempotency_key}".encode('utf-8')
    ).hexdigest()[:32]
    expected_state_json = db_manager._serialize_player(player)

    cached_action = run_async(
        db_manager.get_player_action_result(user_id, 'combat', idempotency_key)
    )
    if cached_action:
        if not cached_action.get('player'):
            return jsonify({'error': cached_action.get('message', 'Combat action failed')}), 409

        def generate_cached_combat_events():
            cached_result = cached_action.get('result') or {}
            try:
                cached_state = enrich_player_state(cached_action['player'])
            except Exception:
                logger.exception('cached combat state enrichment failed user=%s', user_id)
                yield f"data: {json.dumps({'type': 'error', 'code': 'combat_request_failed', 'retriable': True, 'message': CombatExecutionError.safe_message})}\n\n"
                return
            yield f"data: {json.dumps({'type': 'end', 'delivery_mode': COMBAT_DELIVERY_MODE, 'state': cached_state, 'combat_result': cached_result, 'result_id': cached_action.get('result_id') or combat_result_id, 'seq': 1000000})}\n\n"

        return Response(
            stream_with_context(generate_cached_combat_events()),
            mimetype='text/event-stream',
            headers=_combat_response_headers()
        )

    # Validate combat can start
    if player.hp <= 0:
        logger.info('start_combat: player %s hp <=0 (%s)', user_id, player.hp)
        return jsonify({'error': 'Player is defeated and cannot fight'}), 400

    if not player.board or len(player.board) == 0:
        logger.info('start_combat: player %s has empty board', user_id)
        return jsonify({'error': 'No units on board'}), 400

    # Check board size is valid for player level
    if len(player.board) > player.max_board_size:
        logger.info('start_combat: player %s board size %s exceeds max %s', user_id, len(player.board), player.max_board_size)
        return jsonify({'error': f'Too many units on board (max {player.max_board_size})'}), 400

    # Resolve the complete authoritative board at the request boundary.  Do
    # not let the preparation service silently drop an unknown entry and run a
    # partial team.
    try:
        resolved_player_units = resolve_persisted_team_units(player.board, 'player')
    except InvalidCombatInputError as exc:
        logger.warning(
            'start_combat: invalid player team user=%s code=%s detail=%s',
            user_id,
            exc.code,
            exc.detail,
        )
        return jsonify({'error': exc.safe_message, 'code': exc.code}), 400
    if not resolved_player_units:
        logger.info('start_combat: player %s has no valid units on board', user_id)
        return jsonify({'error': 'No valid units on board'}), 400

    def generate_combat_events():
        """Generator for SSE combat events using combat service"""
        try:
            stream_chunks = []
            # Prepare player units
            success, message, player_data = prepare_player_units_for_combat(str(user_id))
            if not success:
                yield f"data: {json.dumps({'type': 'error', 'message': message})}\n\n"
                return

            player_units, player_unit_info, synergies_data = player_data

            # Clear any lingering effects from previous combats (effects should not persist between battles)
            for u in player_units:
                u.effects = []
            # print(f"DEBUG: After clearing effects, player_units effects: {[u.effects for u in player_units]}")

            # Prepare opponent units
            try:
                opponent_units, opponent_unit_info, opponent_info = prepare_opponent_units_for_combat(player)
            except InvalidCombatInputError:
                raise
            except RuntimeError as e:
                # No DB opponent available — send a friendly SSE error and stop the stream
                logger.warning('start_combat: no DB opponent for player %s: %s', user_id, str(e))
                yield f"data: {json.dumps({'type': 'error', 'message': 'No opponent available — please try again later'})}\n\n"
                return
            except Exception as e:
                # Unexpected error — log and inform client
                logger.exception('start_combat: unexpected error preparing opponent for player %s', user_id)
                yield f"data: {json.dumps({'type': 'error', 'message': 'Internal server error preparing opponent'})}\n\n"
                return

            if not player_units or not opponent_units:
                raise InvalidCombatInputError('Prepared combat teams must not be empty')

            # Clear any lingering effects from previous combats (effects should not persist between battles)
            for u in opponent_units:
                u.effects = []

            # Apply per-round buffs before sending units_init
            a_hp, b_hp = prepare_round_buffs(player_units, opponent_units, round_number=1)
            # print(f"DEBUG: After buffs, player_units effects: {[u.effects for u in player_units]}")
            # Update unit_info with applied buffs. Preserve `template_id` and
            # server-side avatar metadata that `prepare_*_for_combat` provided.
            # `prepare_*_for_combat` returned lightweight `player_unit_info`/
            # `opponent_unit_info` which included `template_id`; the subsequent
            # `to_dict()` call would overwrite that — merge them back here.
            orig_player_info_map = {u['id']: u for u in player_unit_info} if player_unit_info else {}
            orig_opp_info_map = {u['id']: u for u in opponent_unit_info} if opponent_unit_info else {}

            player_unit_info = []
            for i, u in enumerate(player_units):
                # CRITICAL: Use a_hp[i] to get HP after per-round buffs were applied
                d = u.to_dict(current_hp=a_hp[i])
                orig = orig_player_info_map.get(d.get('id'))
                if orig:
                    # preserve template_id and avatar if present
                    if 'template_id' in orig and orig.get('template_id'):
                        d['template_id'] = orig.get('template_id')
                    if 'avatar' in orig and orig.get('avatar'):
                        d['avatar'] = orig.get('avatar')
                player_unit_info.append(d)

            opponent_unit_info = []
            for i, u in enumerate(opponent_units):
                # CRITICAL: Use b_hp[i] to get HP after per-round buffs were applied
                d = u.to_dict(current_hp=b_hp[i])
                orig = orig_opp_info_map.get(d.get('id'))
                if orig:
                    if 'template_id' in orig and orig.get('template_id'):
                        d['template_id'] = orig.get('template_id')
                    if 'avatar' in orig and orig.get('avatar'):
                        d['avatar'] = orig.get('avatar')
                opponent_unit_info.append(d)

            # Send initial units state with synergies and trait definitions
            trait_definitions = [{'name': t['name'], 'type': t['type'], 'description': t.get('description', ''), 'thresholds': t['thresholds'], 'threshold_descriptions': t.get('threshold_descriptions', []), 'effects': t.get('modular_effects', [])} for t in game_manager.data.traits]
            logger.info(f"start_combat: sending units_init for player {user_id}")
            stream_chunks.append(f"data: {json.dumps({'type': 'units_init', 'delivery_mode': COMBAT_DELIVERY_MODE, 'player_units': player_unit_info, 'opponent_units': opponent_unit_info, 'synergies': synergies_data, 'traits': trait_definitions, 'opponent': opponent_info, 'game_state': {'player_units': player_unit_info, 'opponent_units': opponent_unit_info}, 'result_id': combat_result_id, 'seq': 0})}\n\n")

            # Start combat
            logger.info(f"start_combat: sending start event for player {user_id}")
            stream_chunks.append(f"data: {json.dumps({'type': 'start', 'delivery_mode': COMBAT_DELIVERY_MODE, 'message': '⚔️ Walka rozpoczyna się!', 'result_id': combat_result_id, 'seq': 0})}\n\n")

            # Combat callback for SSE streaming with timestamp
            def combat_event_handler(event_type: str, data: dict, event_time: float):
                if event_type == 'state_snapshot':
                    print(f"DEBUG: state_snapshot seq: {data.get('seq')}, timestamp: {data.get('timestamp')}, game_state keys: {list(data.get('game_state', {}).keys())}")
                # Use the mapping helper to standardize payloads
                payload = map_event_to_sse_payload(event_type, data)
                if payload is None:
                    raise RuntimeError(
                        f"Unmapped combat event type '{event_type}' at seq={data.get('seq')} keys={sorted(list(data.keys()))}"
                    )
                payload['timestamp'] = float(event_time)
                payload['result_id'] = combat_result_id
                # Normalize simulator UUIDs to an action-scoped identity so a
                # retry with the same idempotency key has the same event IDs.
                payload['event_id'] = f"{combat_result_id}:{len(stream_chunks)}"
                return [json.dumps(payload)]

            # Collect events with timestamps
            events = []  # (event_type, data, event_time)
            all_events_for_debug = []  # For debugging desyncs
            def event_collector(event_type: str, data: dict):
                event_time = data.get('timestamp', 0.0)
                events.append((event_type, data, event_time))

                # Save for debugging (will be written to file after combat)
                debug_event = {
                    'type': event_type,
                    **data
                }
                all_events_for_debug.append(debug_event)

            # Run combat through the single backend combat-service owner.
            try:
                result = run_combat_simulation(
                    player_units,
                    opponent_units,
                    event_callback=event_collector,
                    skip_per_round_buffs=True,
                    attach_game_state=True,
                )
            except CombatError:
                raise
            except Exception as exc:
                raise CombatExecutionError('Combat service raised during request execution', cause=exc) from exc

            # Stream collected events. Apply any immediate gold rewards to player before income calc.
            for event_type, data, event_time in events:
                try:
                    if event_type == 'gold_reward' and data.get('side') == 'team_a':
                        amt = int(data.get('amount', 0) or 0)
                        player.gold += amt
                        print(f"Applied in-combat gold reward: +{amt} to player {user_id}")
                except Exception:
                    pass
                for chunk in combat_event_handler(event_type, data, event_time):
                    logger.debug(f"start_combat: yielding event {event_type} for player {user_id}")
                    stream_chunks.append(f"data: {chunk}\n\n")

            # Combat result
            hp_loss = 0
            post_hp = player.hp
            game_over = False

            # Update player stats
            player.round_number += 1
            # PlayerState owns XP overflow and level-up semantics.  The
            # reward is fixed per completed combat, independent of outcome.
            player.add_xp(2)

            # Apply persistent per-round buffs from traits to units on player's board BEFORE checking winner
            try:
                player_synergies = game_manager.get_board_synergies(player)
                # Calculate buff amplifier for each unit
                unit_amplifiers = {}
                for ui in player.board:
                    unit = next((u for u in game_manager.data.units if u.id == ui.unit_id), None)
                    if not unit:
                        continue
                    amplifier = 1.0
                    for trait_name, (count, tier) in player_synergies.items():
                        trait_obj = next((t for t in game_manager.data.traits if t.get('name') == trait_name), None)
                        if not trait_obj:
                            continue
                        idx = tier - 1
                        effects = trait_obj.get('modular_effects', [])
                        if idx < 0 or idx >= len(effects):
                            continue
                        effect = effects[idx]
                        
                        # Handle modular format (list of trigger objects)
                        if isinstance(effect, list):
                            for trigger_obj in effect:
                                if trigger_obj.get('trigger') == 'passive':
                                    for reward in trigger_obj.get('rewards', []):
                                        if reward.get('type') == 'buff_amplifier':
                                            target = trait_obj.get('target', 'trait')
                                            if target == 'team' or (target == 'trait' and trait_name in unit.factions or trait_name in unit.classes):
                                                amplifier = max(amplifier, float(reward.get('multiplier', 1)))
                    unit_amplifiers[ui.instance_id] = amplifier

            except Exception as e:
                print(f"Error applying buff amplifiers: {e}")

            # Apply permanent buffs from kills - now handled by modular_effect_processor during combat
            # Legacy code removed

            win_bonus = 0
            if result['winner'] == 'team_a':
                # Victory
                player.wins += 1
                win_bonus = 1  # +1 gold bonus for winning
                player.streak += 1

                stream_chunks.append(f"data: {json.dumps({'type': 'victory', 'message': '🎉 ZWYCIĘSTWO!', 'result_id': combat_result_id, 'seq': 999998})}\n\n")

            elif result['winner'] == 'team_b':
                # Defeat - lose HP based on surviving enemy star levels
                defeat = resolve_defeat_hp_mutation(
                    player,
                    result,
                    opponent_units=opponent_units,
                    opponent_level=opponent_info.get('level') if isinstance(opponent_info, dict) else None,
                )
                hp_loss = defeat['hp_loss']
                post_hp = defeat['post_hp']
                player.losses += 1
                player.streak = 0

                if post_hp <= 0:
                    game_over = True
                    stream_chunks.append(f"data: {json.dumps({'type': 'defeat', 'message': f'💀 PRZEGRANA! -{hp_loss} HP. Koniec gry!', 'game_over': True, 'result_id': combat_result_id, 'seq': 999998})}\n\n")
                else:
                    stream_chunks.append(f"data: {json.dumps({'type': 'defeat', 'message': f'💔 PRZEGRANA! -{hp_loss} HP (zostało {post_hp} HP)', 'result_id': combat_result_id, 'seq': 999998})}\n\n")

            # Previously an intermediate 'end' event was sent here to finalize
            # buffering. That prematurely signals the client the stream is
            # complete; remove the intermediate 'end' so the final 'end'
            # (which includes full `state`) is the canonical completion event.

            reward = apply_post_combat_rewards(player, player.round_number, win_bonus)

            # Send gold income notification with breakdown
            gold_breakdown = {
                'type': 'gold_income',
                **reward,
                'seq': 999997
            }
            gold_breakdown['result_id'] = combat_result_id
            stream_chunks.append(f"data: {json.dumps(gold_breakdown)}\n\n")

            # Generate new shop (unless locked)
            if not player.locked_shop:
                game_manager.generate_shop(player)
            else:
                # Unlock shop after combat
                player.locked_shop = False

            # Clear effects after combat to prevent persistence
            for u in player_units + opponent_units:
                u.effects = []

            result_metadata = {
                'winner': result['winner'],
                'win_bonus': win_bonus,
                'hp_loss': hp_loss,
                'post_hp': post_hp,
                'game_over': game_over,
            }
            commit = run_async(db_manager.commit_player_state_action(
                user_id=user_id,
                action_name='combat',
                player=player,
                expected_state_json=expected_state_json,
                idempotency_key=idempotency_key,
                result_id=combat_result_id,
                result=result_metadata,
                message='Combat result committed',
            ))

            # A concurrent retry with the same key resolves to the first
            # committed state/result. Do not emit the locally computed stream.
            if not commit.get('committed'):
                cached_player = commit.get('player')
                if not cached_player:
                    raise PlayerActionConflictError('Cached combat result has no player state')
                cached_state = enrich_player_state(cached_player)
                cached_result = commit.get('result') or result_metadata
                yield f"data: {json.dumps({'type': 'end', 'delivery_mode': COMBAT_DELIVERY_MODE, 'state': cached_state, 'combat_result': cached_result, 'result_id': commit.get('result_id') or combat_result_id, 'seq': 1000000})}\n\n"
                return

            # Post-commit projections must only be created by the request that
            # won the idempotency/CAS boundary.
            board_units = [{'unit_id': ui.unit_id, 'star_level': ui.star_level} for ui in player.board]
            bench_units = [{'unit_id': ui.unit_id, 'star_level': ui.star_level} for ui in player.bench]
            username = payload.get('username', f'Player_{user_id}')
            run_async(db_manager.save_opponent_team(
                user_id=user_id,
                nickname=username,
                board_units=board_units,
                bench_units=bench_units,
                wins=player.wins,
                losses=player.losses,
                level=player.level
            ))
            if game_over:
                team_units = [{'unit_id': ui.unit_id, 'star_level': ui.star_level} for ui in player.board]
                run_async(db_manager.save_to_leaderboard(
                    user_id=user_id,
                    nickname=username,
                    wins=player.wins,
                    losses=player.losses,
                    level=player.level,
                    round_number=player.round_number,
                    team_units=team_units
                ))

            # Send the committed stream and final state. Nothing is emitted
            # before the commit, so a losing concurrent request cannot replay
            # a second reward/result stream.
            for chunk in stream_chunks:
                yield chunk
            state_dict = enrich_player_state(player)
            yield f"data: {json.dumps({'type': 'end', 'delivery_mode': COMBAT_DELIVERY_MODE, 'state': state_dict, 'combat_result': result_metadata, 'result_id': combat_result_id, 'seq': 1000000})}\n\n"

            print(f"Combat finished for user {user_id}, waiting for user to close...")

        except PlayerActionConflictError as exc:
            logger.warning('combat action conflict user=%s: %s', user_id, str(exc))
            yield f"data: {json.dumps({'type': 'error', 'code': 'player_action_conflict', 'retriable': True, 'message': str(exc)})}\n\n"
        except InvalidStoredPlayerStateError as exc:
            logger.exception('invalid stored combat state user=%s', user_id)
            yield f"data: {json.dumps({'type': 'error', 'code': 'invalid_stored_player_state', 'retriable': False, 'message': str(exc)})}\n\n"
        except InvalidCombatInputError as exc:
            logger.warning('combat rejected code=%s detail=%s user=%s', exc.code, exc.detail, user_id)
            yield f"data: {json.dumps(combat_error_sse_payload(exc))}\n\n"
        except CombatExecutionError as exc:
            logger.exception('combat execution failed code=%s user=%s', exc.code, user_id)
            yield f"data: {json.dumps(combat_error_sse_payload(exc))}\n\n"
        except CombatError as exc:
            logger.exception('combat domain failure code=%s user=%s', exc.code, user_id)
            yield f"data: {json.dumps(combat_error_sse_payload(exc))}\n\n"
        except Exception:
            logger.exception('unhandled combat request failure user=%s', user_id)
            yield f"data: {json.dumps({'type': 'error', 'code': 'combat_request_failed', 'retriable': True, 'message': CombatExecutionError.safe_message})}\n\n"

    return Response(
        stream_with_context(generate_combat_events()),
        mimetype='text/event-stream',
        headers=_combat_response_headers()
    )
