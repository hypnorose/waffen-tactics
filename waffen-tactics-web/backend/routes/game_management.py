"""
Game management - handlers for game lifecycle management
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


def get_state(user_id):
    """Get current game state"""
    player = run_async(db_manager.load_player(user_id))

    if not player:
        return jsonify({'error': 'No game found', 'needs_start': True}), 404

    return jsonify(enrich_player_state(player))


def start_game(user_id):
    """Start new game or load existing"""
    player = run_async(db_manager.load_player(user_id))

    if not player:
        # Create new player
        player = game_manager.create_new_player(user_id)
        game_manager.generate_shop(player)
        run_async(db_manager.save_player(player))
        print(f"✨ Created new player: {user_id}")
    else:
        # Generate shop if empty (e.g., after combat without lock)
        if not player.last_shop:
            game_manager.generate_shop(player)
            run_async(db_manager.save_player(player))
            print(f"🛒 Generated shop for existing player: {user_id}")

    return jsonify(enrich_player_state(player))


def reset_game(user_id):
    """Reset game to start over"""
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404

    # Create fresh player
    player = game_manager.create_new_player(user_id)
    game_manager.generate_shop(player)
    run_async(db_manager.save_player(player))

    return jsonify({'message': 'Gra zresetowana!', 'state': enrich_player_state(player)})


def surrender_game(user_id, payload):
    """Surrender current game (lose streak)"""
    player = run_async(db_manager.load_player(user_id))
    if not player:
        return jsonify({'error': 'No game found'}), 404

    # Save to leaderboard before surrendering
    username = payload.get('username', f'Player_{user_id}')
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

    # Reset player to start over (lose streak)
    player = game_manager.create_new_player(user_id)
    game_manager.generate_shop(player)
    run_async(db_manager.save_player(player))

    return jsonify({'message': 'Poddano grę!', 'state': enrich_player_state(player)})


async def init_sample_bots():
    """Initialize sample opponent bots if none exist"""
    has_bots = await db_manager.has_system_opponents()
    if not has_bots:
        print("🤖 Initializing sample opponent bots...")
        await db_manager.add_sample_teams(game_manager.data.units)
        print("✅ Sample bots added!")