import asyncio
from collections import Counter

import pytest

from services import game_actions_service
from services.game_actions_service import buy_unit_action
from waffen_tactics.models.player_state import PlayerState, UnitInstance
from waffen_tactics.services.database import DatabaseManager


def _run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize('item_count', range(7))
def test_buy_action_persists_all_merged_items_and_idempotent_retry(tmp_path, monkeypatch, item_count):
    database = DatabaseManager(str(tmp_path / f'wft188-{item_count}.sqlite3'))
    _run(database.initialize())

    unit_id = game_actions_service.game_manager.data.units[0].id
    unit_cost = game_actions_service.game_manager.data.units[0].cost
    source_items = ['spices', 'safe', 'coat', 'socks', 'notebook', 'orangeade']
    source_units = []
    cursor = 0
    # The purchase below is the third copy that triggers the merge.
    for source_index in range(2):
        item_slice = source_items[cursor:min(cursor + 3, item_count)]
        cursor = min(cursor + 3, item_count)
        source_units.append(
            UnitInstance(
                unit_id=unit_id,
                instance_id=f'persistent-source-{item_count}-{source_index}',
                items=item_slice,
            )
        )
    player = PlayerState(
        user_id=1880 + item_count,
        gold=unit_cost,
        last_shop=[unit_id],
        item_inventory=[],
        bench=source_units,
    )
    _run(database.save_player(player))
    monkeypatch.setattr(game_actions_service, 'db_manager', database)

    user_id = str(1880 + item_count)
    idempotency_key = f'wft188-buy-{item_count}'
    first = buy_unit_action(user_id, unit_id, idempotency_key=idempotency_key)
    retry = buy_unit_action(user_id, unit_id, idempotency_key=idempotency_key)
    stored = _run(database.load_player(1880 + item_count))

    assert first[0] is True
    assert retry[0:2] == first[0:2]
    assert stored is not None
    assert len(stored.bench) == 1
    assert stored.bench[0].star_level == 2
    assert stored.bench[0].items == source_items[:item_count][:3]
    assert stored.item_inventory == source_items[:item_count][3:]
    assert Counter(stored.bench[0].items + stored.item_inventory) == Counter(source_items[:item_count])
