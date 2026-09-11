"""WFT-199 persistent item-combination matrix."""

from __future__ import annotations

import json
from itertools import combinations_with_replacement
from pathlib import Path

import pytest

from services.item_actions import combine_item
from waffen_tactics.models.player_state import PlayerState
from waffen_tactics.services.items import BASE_ITEMS, ITEMS, RECIPES


ROOT = Path(__file__).resolve().parents[3]
MATRIX_PATH = ROOT / "waffen-tactics" / "item_recipe_matrix_wft139.json"


def _load_matrix() -> dict:
    with MATRIX_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


MATRIX = _load_matrix()
ORDERED_PAIRS = []
for recipe in MATRIX["recipes"]:
    first, second = recipe["components"]
    ORDERED_PAIRS.append((first, second, recipe["id"]))
    if first != second:
        ORDERED_PAIRS.append((second, first, recipe["id"]))


def test_combine_item_matrix_has_every_legal_direction():
    expected_pairs = {
        pair
        for pair in combinations_with_replacement(BASE_ITEMS, 2)
        for pair in ({pair} if pair[0] == pair[1] else {pair, tuple(reversed(pair))})
    }
    assert len(ORDERED_PAIRS) == 36
    assert {(first, second) for first, second, _ in ORDERED_PAIRS} == expected_pairs
    assert {recipe_id for _, _, recipe_id in ORDERED_PAIRS} == set(RECIPES.values())


@pytest.mark.parametrize("first,second,expected", ORDERED_PAIRS, ids=lambda value: str(value))
def test_combine_item_matrix_covers_every_legal_direction(first: str, second: str, expected: str):
    player = PlayerState(user_id=199000, item_inventory=[first, second])

    success, _message = combine_item(player, first, second)

    assert success is True
    assert player.item_inventory == [expected]
