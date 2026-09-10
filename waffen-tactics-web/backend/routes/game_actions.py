"""
Game actions - handlers for game actions like buying, selling, moving units
"""
from flask import request, jsonify
from pathlib import Path
import logging
from waffen_tactics.services.database import DatabaseManager, PlayerActionConflictError, InvalidStoredPlayerStateError
from waffen_tactics.services.game_manager import GameManager
from .game_state_utils import run_async, enrich_player_state
from services.game_actions_service import (
    buy_unit_action, sell_unit_action, move_to_board_action, switch_line_action,
    move_to_bench_action, reroll_shop_action, buy_xp_action, toggle_shop_lock_action
)
from services.item_actions import equip_item, combine_item
from waffen_tactics.services.items import all_item_payloads

# Initialize services
DB_PATH = str(Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'waffen_tactics_game.db')
db_manager = DatabaseManager(DB_PATH)
game_manager = GameManager()
logger = logging.getLogger(__name__)


def _internal_error_response(operation, exc):
    """Return a safe action error while retaining server-side correlation."""
    request_id = getattr(request, 'request_id', 'unknown')
    logger.error(
        'player action failed operation=%s request_id=%s error_type=%s',
        operation,
        request_id,
        type(exc).__name__,
    )
    response = jsonify({
        'error': 'Internal server error',
        'code': 'internal_error',
        'request_id': request_id,
    })
    response.headers['X-Request-ID'] = request_id
    return response, 500


def _action_state_response(operation, message, player):
    """Return a successful action only when its derived state is complete."""
    try:
        state = enrich_player_state(player)
        return jsonify({'message': message, 'state': state})
    except Exception as exc:
        return _internal_error_response(f'{operation}.enrich_state', exc)


def _request_json_object():
    """Return a request mapping or a stable 400 response for invalid bodies."""
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        return payload, None

    # Empty bodies remain valid for parameterless actions such as reroll and
    # buy-xp.  A non-empty body must still be valid JSON object data, even
    # when Flask cannot decode it because the media type or JSON is invalid.
    if not request.get_data(cache=True):
        return {}, None

    return None, (
        jsonify({
            'error': 'Invalid request body',
            'code': 'invalid_request_body',
        }),
        400,
    )


def _idempotency_key(payload):
    return request.headers.get('Idempotency-Key') or payload.get('idempotency_key')


def _run_action(action, *args, request_payload=None):
    if request_payload is None:
        request_payload, payload_error = _request_json_object()
        if payload_error:
            return None, payload_error

    try:
        return action(*args, idempotency_key=_idempotency_key(request_payload)), None
    except PlayerActionConflictError as exc:
        return None, (jsonify({'error': str(exc), 'code': 'player_action_conflict'}), 409)
    except InvalidStoredPlayerStateError:
        return None, (jsonify({'error': 'Stored player state is invalid', 'code': 'invalid_stored_state'}), 500)
    except Exception as exc:
        action_name = getattr(action, '__name__', 'unknown_action')
        return None, _internal_error_response(action_name, exc)


def buy_unit(user_id):
    """Buy unit from shop"""
    data, payload_error = _request_json_object()
    if payload_error:
        return payload_error
    unit_id = data.get('unit_id')

    if not unit_id:
        return jsonify({'error': 'Missing unit_id'}), 400

    result, error = _run_action(buy_unit_action, str(user_id), unit_id, request_payload=data)
    if error:
        return error
    success, message, player = result

    if not success:
        return jsonify({'error': message}), 400

    return _action_state_response('buy_unit', message, player)


def sell_unit(user_id):
    """Sell unit from bench or board"""
    data, payload_error = _request_json_object()
    if payload_error:
        return payload_error
    instance_id = data.get('instance_id')

    if not instance_id:
        return jsonify({'error': 'Missing instance_id'}), 400

    result, error = _run_action(sell_unit_action, str(user_id), instance_id, request_payload=data)
    if error:
        return error
    success, message, player = result

    if not success:
        return jsonify({'error': message}), 400

    return _action_state_response('sell_unit', message, player)


def move_to_board(user_id):
    """Move unit from bench to board"""
    data, payload_error = _request_json_object()
    if payload_error:
        return payload_error
    instance_id = data.get('instance_id')
    position = data.get('position', 'front')

    if not instance_id:
        return jsonify({'error': 'Missing instance_id'}), 400

    result, error = _run_action(
        move_to_board_action,
        str(user_id),
        instance_id,
        position,
        request_payload=data,
    )
    if error:
        return error
    success, message, player = result

    if not success:
        return jsonify({'error': message}), 400

    return _action_state_response('move_to_board', message, player)


def switch_line(user_id):
    """Switch unit position on board"""
    data, payload_error = _request_json_object()
    if payload_error:
        return payload_error
    instance_id = data.get('instance_id')
    position = data.get('position')

    if not instance_id or not position:
        return jsonify({'error': 'Missing instance_id or position'}), 400

    result, error = _run_action(
        switch_line_action,
        str(user_id),
        instance_id,
        position,
        request_payload=data,
    )
    if error:
        return error
    success, message, player = result

    if not success:
        return jsonify({'error': message}), 400

    return _action_state_response('switch_line', message, player)


def move_to_bench(user_id):
    """Move unit from board to bench"""
    data, payload_error = _request_json_object()
    if payload_error:
        return payload_error
    instance_id = data.get('instance_id')

    if not instance_id:
        return jsonify({'error': 'Missing instance_id'}), 400

    result, error = _run_action(move_to_bench_action, str(user_id), instance_id, request_payload=data)
    if error:
        return error
    success, message, player = result

    if not success:
        return jsonify({'error': message}), 400

    return _action_state_response('move_to_bench', message, player)


def reroll_shop(user_id):
    """Reroll shop (costs 2 gold)"""
    result, error = _run_action(reroll_shop_action, str(user_id))
    if error:
        return error
    success, message, player = result

    if not success:
        return jsonify({'error': message}), 400

    return _action_state_response('reroll_shop', message, player)


def buy_xp(user_id):
    """Buy XP (costs 4 gold)"""
    result, error = _run_action(buy_xp_action, str(user_id))
    if error:
        return error
    success, message, player = result

    if not success:
        return jsonify({'error': message}), 400

    return _action_state_response('buy_xp', message, player)


def toggle_shop_lock(user_id):
    """Toggle shop lock"""
    result, error = _run_action(toggle_shop_lock_action, str(user_id))
    if error:
        return error
    success, message, player = result

    if not success:
        return jsonify({'error': message}), 400

    return _action_state_response('toggle_shop_lock', message, player)

def get_items():
    return jsonify(all_item_payloads())

def equip_item_route(user_id):
    data, payload_error = _request_json_object()
    if payload_error:
        return payload_error
    result, error = _run_action(
        lambda uid, instance_id, item_id, idempotency_key=None: run_async(
            db_manager.apply_player_action(
                int(uid), 'equip_item',
                lambda player: equip_item(player, instance_id, item_id),
                idempotency_key=idempotency_key,
            )
        ),
        str(user_id), data.get('instance_id'), data.get('item_id'), request_payload=data
    )
    if error:
        return error
    success, message, player = result
    if not success:
        return jsonify({'error': message}), 400
    return _action_state_response('equip_item', message, player)

def combine_item_route(user_id):
    data, payload_error = _request_json_object()
    if payload_error:
        return payload_error
    result, error = _run_action(
        lambda uid, first_item, second_item, idempotency_key=None: run_async(
            db_manager.apply_player_action(
                int(uid), 'combine_item',
                lambda player: combine_item(player, first_item, second_item),
                idempotency_key=idempotency_key,
            )
        ),
        str(user_id), data.get('first_item'), data.get('second_item'), request_payload=data
    )
    if error:
        return error
    success, message, player = result
    if not success:
        return jsonify({'error': message}), 400
    return _action_state_response('combine_item', message, player)
