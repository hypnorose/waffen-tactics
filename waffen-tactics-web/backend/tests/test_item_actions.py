from waffen_tactics.models.player_state import PlayerState
from services.item_actions import combine_item


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
