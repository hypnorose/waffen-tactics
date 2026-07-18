from waffen_tactics.services.items import BASE_ITEMS, ITEMS, combine_item_ids
from waffen_tactics.models.player_state import PlayerState, UnitInstance

def test_all_six_base_items_have_unique_definitions():
    assert len(BASE_ITEMS) == 6
    assert len({item['name'] for item in BASE_ITEMS.values()}) == 6

def test_every_pair_has_a_combined_item():
    base_ids = list(BASE_ITEMS)
    for index, first in enumerate(base_ids):
        for second in base_ids[index + 1:]:
            result = combine_item_ids(first, second)
            assert result in ITEMS
            assert ITEMS[result]['kind'] == 'combined'

def test_unit_items_and_inventory_survive_serialization():
    player = PlayerState(user_id=1, board=[UnitInstance('unit', items=['spices', 'safe'])])
    restored = PlayerState.from_dict(player.to_dict())
    assert restored.board[0].items == ['spices', 'safe']
    assert restored.item_inventory == player.item_inventory
