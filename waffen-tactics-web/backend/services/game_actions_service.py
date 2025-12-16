"""
Game Actions Service - Pure business logic for player game actions
"""
import asyncio
from typing import Dict, Any, Tuple, Optional
from pathlib import Path

from waffen_tactics.services.database import DatabaseManager
from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.models.player_state import PlayerState

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


def buy_unit_action(user_id: str, unit_id: str) -> Tuple[bool, str, Optional[PlayerState]]:
    """
    Buy unit from shop.

    Args:
        user_id: The player's user ID
        unit_id: The ID of the unit to buy

    Returns:
        Tuple of (success, message, player_object)
    """
    player = _run_async(db_manager.load_player(int(user_id)))
    if not player:
        return False, "No game found", None

    success, message = game_manager.buy_unit(player, unit_id)

    if not success:
        return False, message, None

    _run_async(db_manager.save_player(player))

    # Return player object for enrichment
    return True, message, player


def sell_unit_action(user_id: str, instance_id: str) -> Tuple[bool, str, Optional[PlayerState]]:
    """
    Sell unit from bench or board.

    Args:
        user_id: The player's user ID
        instance_id: The instance ID of the unit to sell

    Returns:
        Tuple of (success, message, player_object)
    """
    player = _run_async(db_manager.load_player(int(user_id)))
    if not player:
        return False, "No game found", None

    success, message = game_manager.sell_unit(player, instance_id)

    if not success:
        return False, message, None

    _run_async(db_manager.save_player(player))
    return True, message, player


def move_to_board_action(user_id: str, instance_id: str, position: str = 'front') -> Tuple[bool, str, Optional[PlayerState]]:
    """
    Move unit from bench to board.

    Args:
        user_id: The player's user ID
        instance_id: The instance ID of the unit to move
        position: Position on board ('front' or 'back')

    Returns:
        Tuple of (success, message, player_object)
    """
    player = _run_async(db_manager.load_player(int(user_id)))
    if not player:
        return False, "No game found", None

    success, message = game_manager.move_to_board(player, instance_id, position)

    if not success:
        return False, message, None

    _run_async(db_manager.save_player(player))
    return True, message, player


def switch_line_action(user_id: str, instance_id: str, position: str) -> Tuple[bool, str, Optional[PlayerState]]:
    """
    Switch unit position on board.

    Args:
        user_id: The player's user ID
        instance_id: The instance ID of the unit to move
        position: New position ('front' or 'back')

    Returns:
        Tuple of (success, message, player_object)
    """
    player = _run_async(db_manager.load_player(int(user_id)))
    if not player:
        return False, "No game found", None

    success, message = game_manager.switch_line(player, instance_id, position)

    if not success:
        return False, message, None

    _run_async(db_manager.save_player(player))
    return True, message, player


def move_to_bench_action(user_id: str, instance_id: str) -> Tuple[bool, str, Optional[PlayerState]]:
    """
    Move unit from board to bench.

    Args:
        user_id: The player's user ID
        instance_id: The instance ID of the unit to move

    Returns:
        Tuple of (success, message, player_object)
    """
    player = _run_async(db_manager.load_player(int(user_id)))
    if not player:
        return False, "No game found", None

    success, message = game_manager.move_to_bench(player, instance_id)

    if not success:
        return False, message, None

    _run_async(db_manager.save_player(player))
    return True, message, player


def reroll_shop_action(user_id: str) -> Tuple[bool, str, Optional[PlayerState]]:
    """
    Reroll shop (costs 2 gold).

    Args:
        user_id: The player's user ID

    Returns:
        Tuple of (success, message, player_object)
    """
    player = _run_async(db_manager.load_player(int(user_id)))
    if not player:
        return False, "No game found", None

    success, message = game_manager.reroll_shop(player)

    if not success:
        return False, message, None

    _run_async(db_manager.save_player(player))
    return True, message, player


def buy_xp_action(user_id: str) -> Tuple[bool, str, Optional[PlayerState]]:
    """
    Buy XP (costs 4 gold).

    Args:
        user_id: The player's user ID

    Returns:
        Tuple of (success, message, player_object)
    """
    player = _run_async(db_manager.load_player(int(user_id)))
    if not player:
        return False, "No game found", None

    success, message = game_manager.buy_xp(player)

    if not success:
        return False, message, None

    _run_async(db_manager.save_player(player))
    return True, message, player


def toggle_shop_lock_action(user_id: str) -> Tuple[bool, str, Optional[PlayerState]]:
    """
    Toggle shop lock.

    Args:
        user_id: The player's user ID

    Returns:
        Tuple of (success, message, player_object)
    """
    player = _run_async(db_manager.load_player(int(user_id)))
    if not player:
        return False, "No game found", None

    player.locked_shop = not player.locked_shop
    message = "Sklep zablokowany!" if player.locked_shop else "Sklep odblokowany!"

    _run_async(db_manager.save_player(player))
    return True, message, player