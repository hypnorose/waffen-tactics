import pytest

from waffen_tactics.models.player_state import PlayerState
from waffen_tactics.services.economy import (
    apply_post_combat_rewards,
    calculate_post_combat_rewards,
    milestone_reward_counts,
)
from waffen_tactics.services.items import BASE_ITEMS


@pytest.mark.parametrize(
    ("round_number", "expected_gold", "expected_parts"),
    [
        (1, 0, 0),
        (2, 0, 0),
        (3, 0, 3),
        (4, 0, 0),
        (5, 5, 1),
        (10, 5, 2),
        (15, 5, 1),
        (20, 5, 3),
        (30, 5, 4),
        (31, 0, 0),
    ],
)
def test_milestone_contract(round_number, expected_gold, expected_parts):
    assert milestone_reward_counts(round_number) == (expected_gold, expected_parts)


def test_post_combat_income_uses_win_bonus_before_interest():
    reward = calculate_post_combat_rewards(current_gold=9, completed_round_number=2, win_bonus=1)

    assert reward == {
        "base": 5,
        "interest": 1,
        "milestone": 0,
        "win_bonus": 1,
        "total": 7,
        "item_part_count": 0,
    }


def test_post_combat_rewards_persist_canonical_item_parts():
    player = PlayerState(user_id=1, gold=10, round_number=3, item_inventory=[])

    reward = apply_post_combat_rewards(
        player,
        completed_round_number=3,
        chooser=lambda choices: choices[0],
    )

    assert reward["milestone"] == 0
    assert reward["item_parts"] == [next(iter(BASE_ITEMS))] * 3
    assert player.item_inventory == reward["item_parts"]
    assert player.gold == 16


def test_post_combat_rewards_have_no_parts_on_regular_round():
    player = PlayerState(user_id=1, gold=10, round_number=4, item_inventory=[])

    reward = apply_post_combat_rewards(
        player,
        completed_round_number=4,
        chooser=lambda choices: choices[0],
    )

    assert reward["item_parts"] == []
    assert player.item_inventory == []
