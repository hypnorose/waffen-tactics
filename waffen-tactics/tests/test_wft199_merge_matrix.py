"""WFT-199 merge matrix: bench, board, and mixed source ownership."""

from __future__ import annotations

from collections import Counter

import pytest

from waffen_tactics.models.player_state import PlayerState, UnitInstance
from waffen_tactics.services.game_manager import GameManager


SOURCE_ITEMS = ("spices", "safe", "coat", "socks", "notebook", "orangeade")


def _source_items(item_count: int) -> list[str]:
    return list(SOURCE_ITEMS[:item_count])


def _make_sources(unit_id: str, location: str, item_count: int) -> tuple[list[UnitInstance], list[UnitInstance]]:
    item_ids = _source_items(item_count)
    sources = [
        UnitInstance(
            unit_id=unit_id,
            star_level=1,
            instance_id=f"wft199-{location}-{index}",
            items=item_ids[index * 2 : (index + 1) * 2],
        )
        for index in range(3)
    ]
    if location == "bench":
        return sources, []
    if location == "board":
        return [], sources
    return sources[:2], sources[2:]


@pytest.mark.parametrize("location", ["bench", "board", "mixed"])
@pytest.mark.parametrize("item_count", range(7))
def test_merge_matrix_preserves_items_and_destination(location: str, item_count: int):
    game_manager = GameManager()
    player = PlayerState(user_id=19900 + item_count, item_inventory=[])
    unit_id = game_manager.data.units[0].id
    bench, board = _make_sources(unit_id, location, item_count)
    player.bench.extend(bench)
    player.board.extend(board)

    upgraded = game_manager.try_auto_upgrade(player, unit_id, 1)

    assert upgraded == 2
    assert len(player.bench) + len(player.board) == 1
    result = (player.board or player.bench)[0]
    assert result.star_level == 2
    assert result.items == _source_items(item_count)[:3]
    assert player.item_inventory == _source_items(item_count)[3:]
    assert Counter(result.items + player.item_inventory) == Counter(_source_items(item_count))
    if location in {"board", "mixed"}:
        assert player.board == [result]
        assert player.bench == []
    else:
        assert player.bench == [result]
        assert player.board == []
