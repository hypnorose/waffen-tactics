"""
Game Management Service - Pure business logic for game lifecycle management
"""
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

from waffen_tactics.services.database import DatabaseManager
from waffen_tactics.services.game_manager import GameManager

# Initialize services (these would be injected in a proper DI setup)
DB_PATH = str(Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'waffen_tactics_game.db')
db_manager = DatabaseManager(DB_PATH)
game_manager = GameManager()


def _run_async(coro):
    """Helper to run async functions synchronously"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def get_player_state_data(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get player state data as a pure dict.

    Args:
        user_id: The player's user ID

    Returns:
        Player state dict or None if not found
    """
    player = _run_async(db_manager.load_player(int(user_id)))
    if not player:
        return None

    # Convert player object to dict (simplified version)
    return {
        'user_id': player.user_id,
        'level': player.level,
        'gold': player.gold,
        'wins': player.wins,
        'losses': player.losses,
        'round_number': player.round_number,
        'last_shop': player.last_shop,
        'board': [{'unit_id': ui.unit_id, 'star_level': ui.star_level} for ui in player.board],
        'shop': player.last_shop if player.last_shop else [],
        'needs_start': False
    }


def create_new_game_data(
    user_id: str,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create new game data for a player.

    Args:
        user_id: The player's user ID

    Returns:
        New player state dict
    """
    def mutation(player):
        if not player:
            player = game_manager.create_new_player(int(user_id))
            game_manager.generate_shop(player)
            print(f"✨ Created new player: {user_id}")
        elif not player.last_shop:
            # Generate shop if empty (e.g., after combat without lock).
            game_manager.generate_shop(player)
            print(f"🛒 Generated shop for existing player: {user_id}")
        return True, "Gra rozpoczęta!", player, None

    success, message, _ = _run_async(
        db_manager.apply_player_lifecycle_action(
            int(user_id), 'start_game', mutation, idempotency_key=idempotency_key
        )
    )
    if not success:
        raise ValueError(message)

    return get_player_state_data(user_id)


def reset_player_game_data(
    user_id: str,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reset player game data to start over.

    Args:
        user_id: The player's user ID

    Returns:
        Reset player state dict
    """
    def mutation(player):
        if not player:
            return False, "No game found", None, None
        # Create fresh player.
        next_player = game_manager.create_new_player(int(user_id))
        game_manager.generate_shop(next_player)
        return True, "Gra zresetowana!", next_player, None

    success, message, _ = _run_async(
        db_manager.apply_player_lifecycle_action(
            int(user_id), 'reset_game', mutation, idempotency_key=idempotency_key
        )
    )
    if not success:
        raise ValueError(message)

    return get_player_state_data(user_id)


def surrender_player_game_data(
    user_id: str,
    username: str,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Surrender current game and reset (lose streak).

    Args:
        user_id: The player's user ID
        username: Player's display name for leaderboard

    Returns:
        Reset player state dict
    """
    def mutation(player):
        if not player:
            return False, "No game found", None, None

        # Reset player to start over (lose streak), while recording the old
        # result in the same database transaction.
        team_units = [
            {'unit_id': ui.unit_id, 'star_level': ui.star_level}
            for ui in player.board
        ]
        leaderboard_entry = {
            'user_id': int(user_id),
            'nickname': username,
            'wins': player.wins,
            'losses': player.losses,
            'level': player.level,
            'round_number': player.round_number,
            'team_units': team_units,
        }
        next_player = game_manager.create_new_player(int(user_id))
        game_manager.generate_shop(next_player)
        return True, "Poddano grę!", next_player, leaderboard_entry

    success, message, _ = _run_async(
        db_manager.apply_player_lifecycle_action(
            int(user_id), 'surrender_game', mutation, idempotency_key=idempotency_key
        )
    )
    if not success:
        raise ValueError(message)

    return get_player_state_data(user_id)
