"""
Game Actions Service - Pure business logic for player game actions
"""
import asyncio
from typing import Dict, Any, Tuple, Optional, Callable
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


def _run_player_action(
    user_id: str,
    action_name: str,
    mutation: Callable[[PlayerState], Tuple[bool, str]],
    idempotency_key: Optional[str] = None,
) -> Tuple[bool, str, Optional[PlayerState]]:
    """Run one action through the atomic DB boundary.

    The legacy branch exists only for unit tests that replace ``db_manager``
    with a mock. Production always uses ``DatabaseManager.apply_player_action``.
    """
    if isinstance(db_manager, DatabaseManager):
        return _run_async(
            db_manager.apply_player_action(
                int(user_id), action_name, mutation, idempotency_key=idempotency_key
            )
        )

    player = _run_async(db_manager.load_player(int(user_id)))
    if not player:
        return False, "No game found", None
    success, message = mutation(player)
    if not success:
        return False, message, None
    _run_async(db_manager.save_player(player))
    return True, message, player


def buy_unit_action(user_id: str, unit_id: str, idempotency_key: Optional[str] = None) -> Tuple[bool, str, Optional[PlayerState]]:
    return _run_player_action(
        user_id, "buy_unit", lambda player: game_manager.buy_unit(player, unit_id), idempotency_key
    )


def sell_unit_action(user_id: str, instance_id: str, idempotency_key: Optional[str] = None) -> Tuple[bool, str, Optional[PlayerState]]:
    return _run_player_action(
        user_id, "sell_unit", lambda player: game_manager.sell_unit(player, instance_id), idempotency_key
    )


def move_to_board_action(
    user_id: str,
    instance_id: str,
    position: str = 'front',
    idempotency_key: Optional[str] = None,
) -> Tuple[bool, str, Optional[PlayerState]]:
    return _run_player_action(
        user_id,
        "move_to_board",
        lambda player: game_manager.move_to_board(player, instance_id, position),
        idempotency_key,
    )


def switch_line_action(
    user_id: str,
    instance_id: str,
    position: str,
    idempotency_key: Optional[str] = None,
) -> Tuple[bool, str, Optional[PlayerState]]:
    return _run_player_action(
        user_id,
        "switch_line",
        lambda player: game_manager.switch_line(player, instance_id, position),
        idempotency_key,
    )


def move_to_bench_action(
    user_id: str,
    instance_id: str,
    idempotency_key: Optional[str] = None,
) -> Tuple[bool, str, Optional[PlayerState]]:
    return _run_player_action(
        user_id,
        "move_to_bench",
        lambda player: game_manager.move_to_bench(player, instance_id),
        idempotency_key,
    )


def reroll_shop_action(user_id: str, idempotency_key: Optional[str] = None) -> Tuple[bool, str, Optional[PlayerState]]:
    return _run_player_action(
        user_id, "reroll_shop", lambda player: game_manager.reroll_shop(player), idempotency_key
    )


def buy_xp_action(user_id: str, idempotency_key: Optional[str] = None) -> Tuple[bool, str, Optional[PlayerState]]:
    return _run_player_action(
        user_id, "buy_xp", lambda player: game_manager.buy_xp(player), idempotency_key
    )


def toggle_shop_lock_action(
    user_id: str,
    idempotency_key: Optional[str] = None,
) -> Tuple[bool, str, Optional[PlayerState]]:
    def mutation(player: PlayerState) -> Tuple[bool, str]:
        player.locked_shop = not player.locked_shop
        return True, "Sklep zablokowany!" if player.locked_shop else "Sklep odblokowany!"

    return _run_player_action(user_id, "toggle_shop_lock", mutation, idempotency_key)
