import asyncio

from services import game_actions_service
from services.game_actions_service import buy_unit_action
from waffen_tactics.models.player_state import PlayerState, UnitInstance
from waffen_tactics.services.database import DatabaseManager


def _run(coro):
    return asyncio.run(coro)


def test_buy_action_persists_merged_items_and_idempotent_retry(tmp_path, monkeypatch):
    database = DatabaseManager(str(tmp_path / 'wft188.sqlite3'))
    _run(database.initialize())

    unit_id = game_actions_service.game_manager.data.units[0].id
    unit_cost = game_actions_service.game_manager.data.units[0].cost
    player = PlayerState(
        user_id=188,
        gold=unit_cost,
        last_shop=[unit_id],
        item_inventory=[],
        bench=[
            UnitInstance(
                unit_id=unit_id,
                instance_id='persistent-source-1',
                items=['spices', 'safe'],
            ),
            UnitInstance(
                unit_id=unit_id,
                instance_id='persistent-source-2',
                items=['coat', 'socks'],
            ),
        ],
    )
    _run(database.save_player(player))
    monkeypatch.setattr(game_actions_service, 'db_manager', database)

    first = buy_unit_action('188', unit_id, idempotency_key='wft188-buy-1')
    retry = buy_unit_action('188', unit_id, idempotency_key='wft188-buy-1')
    stored = _run(database.load_player(188))

    assert first[0] is True
    assert retry[0:2] == first[0:2]
    assert stored is not None
    assert len(stored.bench) == 1
    assert stored.bench[0].star_level == 2
    assert stored.bench[0].items == ['spices', 'safe', 'coat']
    assert stored.item_inventory == ['socks']
