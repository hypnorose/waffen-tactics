"""
Game management - handlers for game lifecycle management
"""
from flask import request, jsonify
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'src'))

from waffen_tactics.services.database import DatabaseManager
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


def get_state(user_id):
    """Get current game state"""
    player_data = get_player_state_data(user_id)

    if not player_data:
        return jsonify({'error': 'No game found', 'needs_start': True}), 404

    # Enrich the data with computed fields
    player = run_async(db_manager.load_player(int(user_id)))
    return jsonify(enrich_player_state(player))


def start_game(user_id):
    """Start new game or load existing"""
    try:
        player_data = create_new_game_data(user_id)
        # Enrich the data with computed fields
        player = run_async(db_manager.load_player(int(user_id)))
        return jsonify(enrich_player_state(player))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def reset_game(user_id):
    """Reset game to start over"""
    try:
        player_data = reset_player_game_data(user_id)
        # Enrich the data with computed fields
        player = run_async(db_manager.load_player(int(user_id)))
        return jsonify({'message': 'Gra zresetowana!', 'state': enrich_player_state(player)})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def surrender_game(user_id, payload):
    """Surrender current game (lose streak)"""
    try:
        username = payload.get('username', f'Player_{user_id}')
        player_data = surrender_player_game_data(user_id, username)
        # Enrich the data with computed fields
        player = run_async(db_manager.load_player(int(user_id)))
        return jsonify({'message': 'Poddano grę!', 'state': enrich_player_state(player)})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


async def init_sample_bots():
    """Initialize sample opponent bots if none exist"""
    has_bots = await db_manager.has_system_opponents()
    if not has_bots:
        print("🤖 Initializing sample opponent bots...")
        await db_manager.add_sample_teams(game_manager.data.units)
        print("✅ Sample bots added!")