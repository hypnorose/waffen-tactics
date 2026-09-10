import asyncio

import pytest

from waffen_tactics.models.player_state import PlayerState, UnitInstance
from waffen_tactics.services.database import DatabaseManager
from services.item_actions import combine_item, equip_item


def _run(coro):
    return asyncio.run(coro)


def test_combine_item_accepts_two_copies_for_explicit_a_plus_a_recipe():
    player = PlayerState(user_id=1, item_inventory=['spices', 'spices'])

    success, message = combine_item(player, 'spices', 'spices')

    assert success is True
    assert 'ETF przyprawowy' in message
    assert player.item_inventory == ['etf_przyprawowy']


def test_combine_item_rejects_a_pair_without_two_owned_copies():
    player = PlayerState(user_id=1, item_inventory=['spices'])

    success, message = combine_item(player, 'spices', 'spices')

    assert success is False
    assert message == 'Potrzebujesz dwóch przedmiotów bazowych'


@pytest.mark.parametrize(
    ('first', 'second', 'expected'),
    [
        ('spices', 'safe', 'skrytka_na_oregano'),
        ('safe', 'spices', 'skrytka_na_oregano'),
    ],
)
def test_combine_item_is_symmetric_for_every_legal_direction(first, second, expected):
    player = PlayerState(user_id=1, item_inventory=[first, second])

    success, message = combine_item(player, first, second)

    assert success is True
    assert expected in player.item_inventory
    assert message.endswith('Skrytka na oregano')


def test_combine_item_rejects_non_base_pair_without_mutating_inventory():
    inventory = ['etf_przyprawowy', 'plaszcz_200_welny']
    player = PlayerState(user_id=1, item_inventory=list(inventory))

    success, message = combine_item(player, 'etf_przyprawowy', 'plaszcz_200_welny')

    assert success is False
    assert message == 'Te przedmioty nie mają receptury'
    assert player.item_inventory == inventory


def test_equip_item_accepts_canonical_combined_item_and_consumes_one_inventory_entry():
    unit = UnitInstance('unit', instance_id='unit-1')
    player = PlayerState(user_id=1, board=[unit], item_inventory=['etf_przyprawowy'])

    success, message = equip_item(player, 'unit-1', 'etf_przyprawowy')

    assert success is True
    assert message == 'Założono: ETF przyprawowy'
    assert player.item_inventory == []
    assert unit.items == ['etf_przyprawowy']


def test_equip_item_rejects_stale_id_without_mutating_state():
    unit = UnitInstance('unit', instance_id='unit-1')
    player = PlayerState(user_id=1, board=[unit], item_inventory=['sugar_rush'])

    success, message = equip_item(player, 'unit-1', 'sugar_rush')

    assert success is False
    assert message == 'Nieznany przedmiot'
    assert player.item_inventory == ['sugar_rush']
    assert unit.items == []


def test_equip_item_rejects_full_loadout_without_consuming_item():
    unit = UnitInstance('unit', instance_id='unit-1', items=['spices', 'safe', 'coat'])
    player = PlayerState(user_id=1, board=[unit], item_inventory=['etf_przyprawowy'])

    success, message = equip_item(player, 'unit-1', 'etf_przyprawowy')

    assert success is False
    assert message == 'Jednostka ma już 3 przedmioty'
    assert player.item_inventory == ['etf_przyprawowy']
    assert unit.items == ['spices', 'safe', 'coat']


def test_items_endpoint_exposes_the_same_canonical_six_plus_21_catalog(client):
    response = client.get('/game/items')

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, list)
    assert len(payload) == 27
    assert {item['kind'] for item in payload} == {'base', 'combined'}
    assert len([item for item in payload if item['kind'] == 'base']) == 6
    assert len([item for item in payload if item['kind'] == 'combined']) == 21
    assert not {'sugar_rush', 'seasoned_armor', 'contraband'} & {
        item['id'] for item in payload
    }
    assert all(item['description'] == item['effect']['description'] for item in payload if item['kind'] == 'combined')


def test_combine_item_is_idempotent_at_the_persistent_action_boundary(tmp_path):
    database = DatabaseManager(str(tmp_path / 'item-actions.sqlite3'))
    _run(database.initialize())
    _run(database.save_player(PlayerState(user_id=42, item_inventory=['spices', 'safe'])))
    executions = 0

    def mutation(player):
        nonlocal executions
        executions += 1
        return combine_item(player, 'spices', 'safe')

    first = _run(database.apply_player_action(42, 'combine_item', mutation, 'combine-1'))
    retry = _run(database.apply_player_action(42, 'combine_item', mutation, 'combine-1'))

    assert executions == 1
    assert first[0:2] == retry[0:2] == (True, 'Połączono w: Skrytka na oregano')
    stored = _run(database.load_player(42))
    assert stored.item_inventory == ['skrytka_na_oregano']
