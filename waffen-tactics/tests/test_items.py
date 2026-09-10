import asyncio

import pytest

from waffen_tactics.services.database import DatabaseManager, InvalidStoredPlayerStateError
from waffen_tactics.services.items import BASE_ITEMS, ITEMS, RECIPES, apply_item_stats, combine_item_ids
from waffen_tactics.models.player_state import PlayerState, UnitInstance

def test_all_six_base_items_have_unique_definitions():
    assert len(BASE_ITEMS) == 6
    assert len({item['name'] for item in BASE_ITEMS.values()}) == 6

def test_every_pair_has_a_combined_item():
    base_ids = list(BASE_ITEMS)
    for index, first in enumerate(base_ids):
        for second in base_ids[index:]:
            result = combine_item_ids(first, second)
            assert result in ITEMS
            assert ITEMS[result]['kind'] == 'combined'


def test_runtime_uses_only_the_approved_six_plus_21_matrix():
    assert len(ITEMS) == 27
    assert len(RECIPES) == 21
    assert not {'sugar_rush', 'seasoned_armor', 'contraband'} & set(ITEMS)
    assert all(item['content_version'] == 'wft139-approved-2026-09-10' for item in ITEMS.values())
    assert all(item['effect'] is None for item in BASE_ITEMS.values())
    assert all(item['effect'] for item in ITEMS.values() if item['kind'] == 'combined')


def test_item_stats_are_applied_by_one_shared_helper_and_unknown_ids_fail_closed():
    stats = apply_item_stats({'hp': 100, 'attack': 10, 'defense': 5}, ['spices', 'plaszcz_200_welny'])
    assert stats['attack'] == 18
    assert stats['hp'] == 700

    import pytest
    with pytest.raises(ValueError, match='Unknown equipped item'):
        apply_item_stats(stats, ['sugar_rush'])

def test_unit_items_and_inventory_survive_serialization():
    player = PlayerState(user_id=1, board=[UnitInstance('unit', items=['spices', 'safe'])])
    restored = PlayerState.from_dict(player.to_dict())
    assert restored.board[0].items == ['spices', 'safe']
    assert restored.item_inventory == player.item_inventory


def test_database_round_trip_preserves_all_21_canonical_combined_item_ids(tmp_path):
    combined_ids = [item_id for item_id, item in ITEMS.items() if item['kind'] == 'combined']
    assert len(combined_ids) == 21

    player = PlayerState(
        user_id=21,
        item_inventory=combined_ids,
        board=[UnitInstance('unit', items=['spices', 'plaszcz_200_welny'])],
    )
    database = DatabaseManager(str(tmp_path / 'player-state.sqlite3'))
    asyncio.run(database.initialize())
    asyncio.run(database.save_player(player))

    restored = asyncio.run(database.load_player(21))

    assert restored is not None
    assert restored.item_inventory == combined_ids
    assert restored.board[0].items == ['spices', 'plaszcz_200_welny']


def test_persistence_rejects_legacy_or_unknown_item_ids_without_silent_migration():
    with pytest.raises(ValueError, match='Legacy item ID'):
        PlayerState.from_dict({'user_id': 1, 'item_inventory': ['sugar_rush']})

    with pytest.raises(ValueError, match='Unknown persistent item ID'):
        PlayerState.from_dict({'user_id': 1, 'item_inventory': ['not-in-catalog']})

    with pytest.raises(ValueError, match='Unknown persistent item ID'):
        PlayerState.from_dict({'user_id': 1, 'item_inventory': [['not-an-id']]})


def test_database_save_fails_closed_for_unknown_item_ids(tmp_path):
    database = DatabaseManager(str(tmp_path / 'invalid-player-state.sqlite3'))
    player = PlayerState(user_id=22, item_inventory=['not-in-catalog'])

    with pytest.raises(InvalidStoredPlayerStateError):
        asyncio.run(database.save_player(player))


def test_persistence_rejects_more_than_three_equipped_items():
    with pytest.raises(ValueError, match='3-item limit'):
        PlayerState.from_dict({
            'user_id': 1,
            'board': [{
                'unit_id': 'unit',
                'items': ['spices', 'orangeade', 'coat', 'safe'],
            }],
        })


def test_persistence_does_not_store_derived_or_combat_only_unit_state():
    unit = UnitInstance('unit', items=['spices'])
    unit.base_stats = {'hp': 1}
    unit.buffed_stats = {'hp': 2}
    unit.active_effects = [{'type': 'stun'}]
    unit.combat_counter = 4
    player = PlayerState(user_id=23, board=[unit])

    payload = player.to_dict()
    restored = PlayerState.from_dict(payload)

    assert 'base_stats' not in payload['board'][0]
    assert 'buffed_stats' not in payload['board'][0]
    assert not hasattr(restored.board[0], 'active_effects')
    assert not hasattr(restored.board[0], 'combat_counter')
