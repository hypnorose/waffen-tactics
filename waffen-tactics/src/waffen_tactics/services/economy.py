"""Authoritative post-combat economy and milestone reward rules."""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from .items import BASE_ITEMS

if TYPE_CHECKING:
    from ..models.player_state import PlayerState


BASE_ROUND_INCOME = 5
MAX_INTEREST = 5
MILESTONE_INTERVAL = 5
EARLY_ITEM_PART_ROUND = 3


def _require_non_negative_integer(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _require_completed_round(round_number: int) -> None:
    if isinstance(round_number, bool) or not isinstance(round_number, int) or round_number < 1:
        raise ValueError("completed_round_number must be a positive integer")


def milestone_reward_counts(completed_round_number: int) -> tuple[int, int]:
    """Return ``(gold, item_part_count)`` for a completed round.

    Round three is the explicit early item reward. Every fifth round grants
    fixed milestone gold and one item part. The 10th, 20th, 30th, and later
    tenth-round milestones add one, two, three, and later extra parts.
    """
    _require_completed_round(completed_round_number)

    if completed_round_number == EARLY_ITEM_PART_ROUND:
        return 0, 3
    if completed_round_number % MILESTONE_INTERVAL == 0:
        extra_parts = completed_round_number // 10 if completed_round_number % 10 == 0 else 0
        return 5, 1 + extra_parts
    return 0, 0


def calculate_post_combat_rewards(
    current_gold: int,
    completed_round_number: int,
    win_bonus: int = 0,
) -> dict[str, int]:
    """Calculate the complete post-combat income without mutating state.

    ``current_gold`` is the balance before applying ``win_bonus``. Interest
    therefore correctly uses the balance after that bonus, matching the live
    combat contract.
    """
    _require_non_negative_integer(current_gold, "current_gold")
    _require_completed_round(completed_round_number)
    _require_non_negative_integer(win_bonus, "win_bonus")

    interest = min(MAX_INTEREST, (current_gold + win_bonus) // 10)
    milestone_gold, item_part_count = milestone_reward_counts(completed_round_number)
    return {
        "base": BASE_ROUND_INCOME,
        "interest": interest,
        "milestone": milestone_gold,
        "win_bonus": win_bonus,
        "total": BASE_ROUND_INCOME + interest + milestone_gold + win_bonus,
        "item_part_count": item_part_count,
    }


def draw_item_parts(
    count: int,
    chooser: Callable[[Sequence[str]], str] | None = None,
) -> list[str]:
    """Draw base-item IDs from the canonical item set."""
    _require_non_negative_integer(count, "count")
    choices = tuple(BASE_ITEMS)
    pick = chooser or random.choice
    parts: list[str] = []
    for _ in range(count):
        item_id = pick(choices)
        if not isinstance(item_id, str) or item_id not in BASE_ITEMS:
            raise ValueError(f"Item-part chooser returned an unknown base item: {item_id!r}")
        parts.append(item_id)
    return parts


def apply_post_combat_rewards(
    player: "PlayerState",
    completed_round_number: int,
    win_bonus: int = 0,
    chooser: Callable[[Sequence[str]], str] | None = None,
) -> dict[str, int | list[str]]:
    """Apply post-combat income and item parts to a player state."""
    reward = calculate_post_combat_rewards(player.gold, completed_round_number, win_bonus)
    parts = draw_item_parts(reward["item_part_count"], chooser)

    if not isinstance(player.item_inventory, list):
        raise TypeError("PlayerState.item_inventory must be a list")
    player.item_inventory.extend(parts)
    player.gold += reward["total"]

    return {
        "base": reward["base"],
        "interest": reward["interest"],
        "milestone": reward["milestone"],
        "win_bonus": reward["win_bonus"],
        "total": reward["total"],
        "item_parts": parts,
    }
