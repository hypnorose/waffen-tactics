"""
Game actions - handlers for game actions like buying, selling, moving units
"""
from flask import request, jsonify
from pathlib import Path
from waffen_tactics.services.database import DatabaseManager
from waffen_tactics.services.game_manager import GameManager
from .game_state_utils import run_async, enrich_player_state

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

    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404

    success, message = game_manager.buy_unit(player, unit_id)

    if not success:
        return jsonify({'error': message}), 400

    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})


def sell_unit(user_id):
    """Sell unit from bench or board"""
    data = request.json
    instance_id = data.get('instance_id')

    if not instance_id:
        return jsonify({'error': 'Missing instance_id'}), 400

    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404

    success, message = game_manager.sell_unit(player, instance_id)

    if not success:
        return jsonify({'error': message}), 400

    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})


def move_to_board(user_id):
    """Move unit from bench to board"""
    data = request.json
    instance_id = data.get('instance_id')
    position = data.get('position', 'front')

    if not instance_id:
        return jsonify({'error': 'Missing instance_id'}), 400

    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404

    success, message = game_manager.move_to_board(player, instance_id, position)

    if not success:
        return jsonify({'error': message}), 400

    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})


def switch_line(user_id):
    """Switch unit position on board"""
    data = request.json
    instance_id = data.get('instance_id')
    position = data.get('position')

    if not instance_id or not position:
        return jsonify({'error': 'Missing instance_id or position'}), 400

    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404

    success, message = game_manager.switch_line(player, instance_id, position)

    if not success:
        return jsonify({'error': message}), 400

    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})


def move_to_bench(user_id):
    """Move unit from board to bench"""
    data = request.json
    instance_id = data.get('instance_id')

    if not instance_id:
        return jsonify({'error': 'Missing instance_id'}), 400

    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404

    success, message = game_manager.move_to_bench(player, instance_id)

    if not success:
        return jsonify({'error': message}), 400

    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})


def reroll_shop(user_id):
    """Reroll shop (costs 2 gold)"""
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404

    success, message = game_manager.reroll_shop(player)

    if not success:
        return jsonify({'error': message}), 400

    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})


def buy_xp(user_id):
    """Buy XP (costs 4 gold)"""
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404

    success, message = game_manager.buy_xp(player)

    if not success:
        return jsonify({'error': message}), 400

    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})


def toggle_shop_lock(user_id):
    """Toggle shop lock"""
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404

    player.locked_shop = not player.locked_shop
    message = "Sklep zablokowany!" if player.locked_shop else "Sklep odblokowany!"

    run_async(db_manager.save_player(player))
    return jsonify({'message': message, 'state': enrich_player_state(player)})