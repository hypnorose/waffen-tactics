"""
Game management - handlers for game lifecycle management
"""
from flask import request, jsonify
from pathlib import Path
import sys
import logging

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'src'))

from waffen_tactics.services.database import (
    DatabaseManager,
    InvalidStoredPlayerStateError,
    PlayerActionConflictError,
)
from waffen_tactics.services.game_manager import GameManager
from .game_state_utils import run_async, enrich_player_state
from services.game_management_service import (
    get_player_state_data,
    create_new_game_data,
    reset_player_game_data,
    surrender_player_game_data
)

# Initialize services
DB_PATH = str(Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'waffen_tactics_game.db')
db_manager = DatabaseManager(DB_PATH)
game_manager = GameManager()
logger = logging.getLogger(__name__)


def _internal_error_response(operation, exc):
    """Return a safe lifecycle error while retaining server-side correlation."""
    request_id = getattr(request, 'request_id', 'unknown')
    logger.error(
        'game lifecycle failed operation=%s request_id=%s error_type=%s',
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


def _request_idempotency_key():
    """Resolve lifecycle retry identity with header precedence."""
    header_key = request.headers.get('Idempotency-Key')
    if header_key:
        return header_key
    payload = request.get_json(silent=True)
    return payload.get('idempotency_key') if isinstance(payload, dict) else None


def get_state(user_id):
    """Get current game state"""
    try:
        player_data = get_player_state_data(user_id)

        if not player_data:
            return jsonify({'error': 'No game found', 'needs_start': True}), 404

        # Enrich the data with computed fields
        player = run_async(db_manager.load_player(int(user_id)))
        return jsonify(enrich_player_state(player))
    except Exception as exc:
        return _internal_error_response('get_state', exc)


def start_game(user_id):
    """Start new game or load existing"""
    try:
        player_data = create_new_game_data(
            user_id,
            idempotency_key=_request_idempotency_key(),
        )
        # Enrich the data with computed fields
        player = run_async(db_manager.load_player(int(user_id)))
        return jsonify(enrich_player_state(player))
    except PlayerActionConflictError as exc:
        return jsonify({'error': str(exc), 'code': 'player_action_conflict'}), 409
    except InvalidStoredPlayerStateError:
        return jsonify({'error': 'Stored player state is invalid', 'code': 'invalid_stored_state'}), 500
    except Exception as exc:
        return _internal_error_response('start_game', exc)


def reset_game(user_id):
    """Reset game to start over"""
    try:
        player_data = reset_player_game_data(
            user_id,
            idempotency_key=_request_idempotency_key(),
        )
        # Enrich the data with computed fields
        player = run_async(db_manager.load_player(int(user_id)))
        return jsonify({'message': 'Gra zresetowana!', 'state': enrich_player_state(player)})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except PlayerActionConflictError as exc:
        return jsonify({'error': str(exc), 'code': 'player_action_conflict'}), 409
    except InvalidStoredPlayerStateError:
        return jsonify({'error': 'Stored player state is invalid', 'code': 'invalid_stored_state'}), 500
    except Exception as exc:
        return _internal_error_response('reset_game', exc)


def surrender_game(user_id, payload):
    """Surrender current game (lose streak)"""
    try:
        username = payload.get('username', f'Player_{user_id}')
        player_data = surrender_player_game_data(
            user_id,
            username,
            idempotency_key=_request_idempotency_key(),
        )
        # Enrich the data with computed fields
        player = run_async(db_manager.load_player(int(user_id)))
        return jsonify({'message': 'Poddano grę!', 'state': enrich_player_state(player)})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except PlayerActionConflictError as exc:
        return jsonify({'error': str(exc), 'code': 'player_action_conflict'}), 409
    except InvalidStoredPlayerStateError:
        return jsonify({'error': 'Stored player state is invalid', 'code': 'invalid_stored_state'}), 500
    except Exception as exc:
        return _internal_error_response('surrender_game', exc)


async def init_sample_bots():
    """Initialize sample opponent bots if none exist"""
    has_bots = await db_manager.has_system_opponents()
    if not has_bots:
        print("🤖 Initializing sample opponent bots...")
        await db_manager.add_sample_teams(game_manager.data.units)
        print("✅ Sample bots added!")
