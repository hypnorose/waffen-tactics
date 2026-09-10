"""Regression tests for the post-combat XP contract."""

import ast
from pathlib import Path
from unittest.mock import patch

import pytest

from services.combat_service import process_combat_results
from waffen_tactics.models.player_state import PlayerState


def _process_result(winner: str) -> PlayerState:
    player = PlayerState(
        user_id=42,
        level=1,
        xp=1,
        hp=100,
        locked_shop=True,
    )
    result = {'winner': winner}
    if winner == 'team_b':
        result.update({'surviving_star_sum': 1, 'opponent_level': 1})

    with patch('services.combat_service.game_manager') as game_manager:
        game_manager.get_board_synergies.return_value = {}
        process_combat_results(player, result, {})

    return player


@pytest.mark.parametrize('winner', ['team_a', 'team_b'])
def test_each_completed_combat_awards_exactly_two_xp_and_uses_canonical_level_up(winner):
    player = _process_result(winner)

    # Level 1 requires 2 XP. Starting at 1 and receiving exactly 2 leaves one
    # point of overflow after the canonical PlayerState level-up.
    assert player.level == 2
    assert player.xp == 1
    assert player.round_number == 2


def test_victory_and_defeat_have_identical_xp_progression():
    victory = _process_result('team_a')
    defeat = _process_result('team_b')

    assert (victory.level, victory.xp) == (defeat.level, defeat.xp) == (2, 1)


def test_production_route_delegates_xp_and_level_up_to_player_state():
    route_path = Path(__file__).parents[1] / 'routes' / 'game_combat.py'
    tree = ast.parse(route_path.read_text(encoding='utf-8'))
    start_combat = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == 'start_combat'
    )

    direct_xp_mutations = [
        node for node in ast.walk(start_combat)
        if isinstance(node, ast.AugAssign)
        and isinstance(node.target, ast.Attribute)
        and node.target.attr == 'xp'
    ]
    add_xp_calls = [
        node for node in ast.walk(start_combat)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == 'add_xp'
    ]

    assert direct_xp_mutations == []
    assert len(add_xp_calls) == 1
    assert isinstance(add_xp_calls[0].args[0], ast.Constant)
    assert add_xp_calls[0].args[0].value == 2
