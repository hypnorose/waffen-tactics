

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import jwt
import datetime
import os
import sys
import asyncio
from pathlib import Path
from functools import wraps
from dotenv import load_dotenv
from flask import Blueprint, request, jsonify

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'))
# Auth exchange endpoint moved to `routes.auth` (registered at `/auth/exchange`)
from waffen_tactics.services.database import DatabaseManager
from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.models.player_state import PlayerState

# Import shared combat system
from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit
from routes.auth import auth_bp, require_auth, verify_token

# Import refactored modules
from .game_state_utils import run_async, enrich_player_state
from .game_management import get_state, start_game, reset_game, surrender_game, init_sample_bots
from .game_actions import buy_unit, sell_unit, move_to_board, switch_line, move_to_bench, reroll_shop, buy_xp, toggle_shop_lock
from .game_data import get_leaderboard, get_leaderboard_data, get_units, get_traits
from .game_combat import start_combat

# Persistent stacking rules
HP_STACK_PER_STAR = 5  # default
DB_PATH = str(Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'waffen_tactics_game.db')
db_manager = DatabaseManager(DB_PATH)
game_manager = GameManager()
game_bp = Blueprint('game', __name__)

# Routes

@game_bp.route('/state', methods=['GET'])
@require_auth
def get_state_route(user_id):
    print(f"🎯 get_state_route called with user_id: {user_id}")
    return get_state(user_id)

@game_bp.route('/start', methods=['POST'])
@require_auth
def start_game_route(user_id):
    return start_game(user_id)

@game_bp.route('/buy', methods=['POST'])
@require_auth
def buy_unit_route(user_id):
    return buy_unit(user_id)

@game_bp.route('/sell', methods=['POST'])
@require_auth
def sell_unit_route(user_id):
    return sell_unit(user_id)

@game_bp.route('/move-to-board', methods=['POST'])
@require_auth
def move_to_board_route(user_id):
    return move_to_board(user_id)

@game_bp.route('/switch-line', methods=['POST'])
@require_auth
def switch_line_route(user_id):
    return switch_line(user_id)

@game_bp.route('/move-to-bench', methods=['POST'])
@require_auth
def move_to_bench_route(user_id):
    return move_to_bench(user_id)

@game_bp.route('/reroll', methods=['POST'])
@require_auth
def reroll_shop_route(user_id):
    return reroll_shop(user_id)

@game_bp.route('/buy-xp', methods=['POST'])
@require_auth
def buy_xp_route(user_id):
    return buy_xp(user_id)

@game_bp.route('/toggle-lock', methods=['POST'])
@require_auth
def toggle_shop_lock_route(user_id):
    return toggle_shop_lock(user_id)

@game_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard_route():
    # Support optional ?period=24h|all (default to last 24h)
    period = request.args.get('period', '24h')
    try:
        leaderboard = get_leaderboard_data(period=period)
        return jsonify(leaderboard)
    except Exception as e:
        print('Error fetching leaderboard:', e)
        return jsonify([]), 500

@game_bp.route('/units', methods=['GET'])
def get_units_route():
    return get_units()

@game_bp.route('/traits', methods=['GET'])
def get_traits_route():
    return get_traits()

@game_bp.route('/combat', methods=['GET'])
def start_combat_route():
    return start_combat()

@game_bp.route('/reset', methods=['POST'])
@require_auth
def reset_game_route(user_id):
    return reset_game(user_id)

@game_bp.route('/surrender', methods=['POST'])
@require_auth
def surrender_game_route(user_id):
    # Get payload for username
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    payload = verify_token(token)
    return surrender_game(user_id, payload)


# Player avatar caching endpoint
@game_bp.route('/player-avatar', methods=['POST'])
@require_auth
def player_avatar_route(user_id):
    """Ensure player's avatar PNG is downloaded into `public/avatars/players/{user_id}.png`.
    If file already exists, returns cached path. Otherwise downloads from provided
    `avatarUrl` (or derives it from the JWT payload) and saves it.
    """
    try:
        data = request.json or {}
        avatar_url = data.get('avatarUrl')

        # Try to obtain avatar hash from token payload if URL not provided
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        payload = verify_token(token)
        avatar_hash = payload.get('avatar')
        if not avatar_url and avatar_hash:
            # Build Discord CDN URL
            avatar_url = f"https://cdn.discordapp.com/avatars/{payload.get('user_id')}/{avatar_hash}.png?size=256"

        if not avatar_url:
            return jsonify({'error': 'No avatar URL available'}), 400

        # Prepare destination directory
        public_dir = Path(__file__).parent.parent.parent / 'public' / 'avatars' / 'players'
        public_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{user_id}.png"
        dest = public_dir / filename

        if dest.exists():
            # Update DB reference to local avatar path as well
            try:
                run_async(db_manager.set_opponent_avatar_local(int(user_id), f"players/{filename}"))
            except Exception:
                pass
            return jsonify({'avatarUrl': f"/avatars/players/{filename}", 'cached': True})

        # Download the avatar
        print(f"⬇️ Downloading avatar for user {user_id} from {avatar_url}")
        resp = requests.get(avatar_url, timeout=10)
        if resp.status_code != 200:
            return jsonify({'error': 'Failed to download avatar', 'status': resp.status_code}), 400

        # Save file
        with open(dest, 'wb') as fh:
            fh.write(resp.content)
        # Persist DB mapping to avatar_local for this user
        try:
            run_async(db_manager.set_opponent_avatar_local(int(user_id), f"players/{filename}"))
        except Exception:
            pass

        return jsonify({'avatarUrl': f"/avatars/players/{filename}", 'cached': False})
    except Exception as e:
        print(f"❌ Error in player_avatar_route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
