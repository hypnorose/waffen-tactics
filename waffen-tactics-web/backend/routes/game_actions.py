"""
Game actions - handlers for game actions like buying, selling, moving units
"""
from flask import request, jsonify
from pathlib import Path
from waffen_tactics.services.database import DatabaseManager
from waffen_tactics.services.game_manager import GameManager
from .game_state_utils import run_async, enrich_player_state
from services.game_actions_service import (
    buy_unit_action, sell_unit_action, move_to_board_action, switch_line_action,
    move_to_bench_action, reroll_shop_action, buy_xp_action, toggle_shop_lock_action
)

# Initialize services
DB_PATH = str(Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'waffen_tactics_game.db')
db_manager = DatabaseManager(DB_PATH)
game_manager = GameManager()


def buy_unit(user_id):
    """Buy unit from shop"""
    data = request.json
    unit_id = data.get('unit_id')

    if not unit_id:
        return jsonify({'error': 'Missing unit_id'}), 400

    success, message, player = buy_unit_action(str(user_id), unit_id)

    if not success:
        return jsonify({'error': message}), 400

    return jsonify({'message': message, 'state': enrich_player_state(player)})


def sell_unit(user_id):
    """Sell unit from bench or board"""
    data = request.json
    instance_id = data.get('instance_id')

    if not instance_id:
        return jsonify({'error': 'Missing instance_id'}), 400

    success, message, player = sell_unit_action(str(user_id), instance_id)

    if not success:
        return jsonify({'error': message}), 400

    return jsonify({'message': message, 'state': enrich_player_state(player)})


def move_to_board(user_id):
    """Move unit from bench to board"""
    data = request.json
    instance_id = data.get('instance_id')
    position = data.get('position', 'front')

    if not instance_id:
        return jsonify({'error': 'Missing instance_id'}), 400

    success, message, player = move_to_board_action(str(user_id), instance_id, position)

    if not success:
        return jsonify({'error': message}), 400

    return jsonify({'message': message, 'state': enrich_player_state(player)})


def switch_line(user_id):
    """Switch unit position on board"""
    data = request.json
    instance_id = data.get('instance_id')
    position = data.get('position')

    if not instance_id or not position:
        return jsonify({'error': 'Missing instance_id or position'}), 400

    success, message, player = switch_line_action(str(user_id), instance_id, position)

    if not success:
        return jsonify({'error': message}), 400

    return jsonify({'message': message, 'state': enrich_player_state(player)})


def move_to_bench(user_id):
    """Move unit from board to bench"""
    data = request.json
    instance_id = data.get('instance_id')

    if not instance_id:
        return jsonify({'error': 'Missing instance_id'}), 400

    success, message, player = move_to_bench_action(str(user_id), instance_id)

    if not success:
        return jsonify({'error': message}), 400

    return jsonify({'message': message, 'state': enrich_player_state(player)})


def reroll_shop(user_id):
    """Reroll shop (costs 2 gold)"""
    success, message, player = reroll_shop_action(str(user_id))

    if not success:
        return jsonify({'error': message}), 400

    return jsonify({'message': message, 'state': enrich_player_state(player)})


def buy_xp(user_id):
    """Buy XP (costs 4 gold)"""
    success, message, player = buy_xp_action(str(user_id))

    if not success:
        return jsonify({'error': message}), 400

    return jsonify({'message': message, 'state': enrich_player_state(player)})


def toggle_shop_lock(user_id):
    """Toggle shop lock"""
    success, message, player = toggle_shop_lock_action(str(user_id))

    if not success:
        return jsonify({'error': message}), 400

    return jsonify({'message': message, 'state': enrich_player_state(player)})