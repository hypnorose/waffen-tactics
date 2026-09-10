import asyncio

from waffen_tactics.models.player_state import PlayerState, UnitInstance
from waffen_tactics.services.database import DatabaseManager
from services.item_actions import equip_item


def _run(coro):
    return asyncio.run(coro)


def test_equip_auto_combines_two_different_base_items_from_the_canonical_matrix():
    unit = UnitInstance('unit', instance_id='unit-1', items=['spices'])
    player = PlayerState(user_id=1, board=[unit], item_inventory=['safe', 'orangeade'])

    success, message = equip_item(player, 'unit-1', 'safe')

    assert success is True
    assert message == 'Połączono i założono: Skrytka na oregano'
    assert player.item_inventory == ['orangeade']
    assert unit.items == ['skrytka_na_oregano']


def test_equip_auto_combines_a_plus_a():
    unit = UnitInstance('unit', instance_id='unit-1', items=['spices'])
    player = PlayerState(user_id=2, board=[unit], item_inventory=['spices', 'safe'])

    success, message = equip_item(player, 'unit-1', 'spices')

    assert success is True
    assert message == 'Połączono i założono: ETF przyprawowy'
    assert player.item_inventory == ['safe']
    assert unit.items == ['etf_przyprawowy']


def test_equip_uses_first_compatible_partner_in_slot_order():
    unit = UnitInstance('unit', instance_id='unit-1', items=['spices', 'safe'])
    player = PlayerState(user_id=3, board=[unit], item_inventory=['coat'])

    success, _ = equip_item(player, 'unit-1', 'coat')

    assert success is True
    assert player.item_inventory == []
    assert unit.items == ['plaszcz_ze_100_bawelny', 'safe']


def test_equip_can_combine_into_a_full_three_slot_loadout():
    unit = UnitInstance('unit', instance_id='unit-1', items=['spices', 'safe', 'coat'])
    player = PlayerState(user_id=4, board=[unit], item_inventory=['orangeade'])

    success, _ = equip_item(player, 'unit-1', 'orangeade')

    assert success is True
    assert player.item_inventory == []
    assert unit.items == ['helena_o_smaku_kurkumy', 'safe', 'coat']


def test_equip_rejects_a_full_loadout_without_a_compatible_base_partner():
    unit = UnitInstance('unit', instance_id='unit-1', items=['spices', 'safe', 'coat'])
    player = PlayerState(user_id=5, board=[unit], item_inventory=['etf_przyprawowy'])

    success, message = equip_item(player, 'unit-1', 'etf_przyprawowy')

    assert success is False
    assert message == 'Jednostka ma już 3 przedmioty'
    assert player.item_inventory == ['etf_przyprawowy']
    assert unit.items == ['spices', 'safe', 'coat']


def test_equip_persists_auto_combine_atomically_and_is_idempotent(tmp_path):
    database = DatabaseManager(str(tmp_path / 'auto-combine.sqlite3'))
    _run(database.initialize())
    _run(database.save_player(PlayerState(
        user_id=6,
        board=[UnitInstance('unit', instance_id='unit-1', items=['spices'])],
        item_inventory=['safe'],
    )))
    executions = 0

    def mutation(player):
        nonlocal executions
        executions += 1
        return equip_item(player, 'unit-1', 'safe')

    first = _run(database.apply_player_action(6, 'equip_item', mutation, 'equip-1'))
    retry = _run(database.apply_player_action(6, 'equip_item', mutation, 'equip-1'))
    stored = _run(database.load_player(6))

    assert executions == 1
    assert first[0:2] == retry[0:2] == (True, 'Połączono i założono: Skrytka na oregano')
    assert stored is not None
    assert stored.item_inventory == []
    assert stored.board[0].items == ['skrytka_na_oregano']
