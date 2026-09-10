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
