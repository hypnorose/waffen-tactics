import pytest

from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.models.player_state import PlayerState, UnitInstance


@pytest.fixture
def gm():
    return GameManager()


def test_generate_shop_and_buy_unit_success(gm):
    player = PlayerState(user_id=1)
    # generate shop offers
    offers = gm.generate_shop(player, force_new=True)
    assert isinstance(offers, list)
    assert len(offers) > 0

    # pick first offered unit id
    unit_id = offers[0]
    unit_obj = next((u for u in gm.data.units if u.id == unit_id), None)
    assert unit_obj is not None
    start_gold = player.gold

    ok, msg = gm.buy_unit(player, unit_id)
    assert ok is True
    assert player.gold == start_gold - unit_obj.cost
    assert any(u.unit_id == unit_id for u in player.bench)


def test_buy_unit_not_in_shop(gm):
    player = PlayerState(user_id=2)
    ok, msg = gm.buy_unit(player, "nonexistent_unit")
    assert not ok
    assert isinstance(msg, str)


def test_sell_unit_from_bench(gm):
    player = PlayerState(user_id=3)
    unit_sample = gm.data.units[0]
    inst = UnitInstance(unit_id=unit_sample.id, star_level=2)
    player.bench.append(inst)
    start_gold = player.gold

    ok, msg = gm.sell_unit(player, inst.instance_id)
    assert ok
    assert player.gold == start_gold + unit_sample.cost * inst.star_level
    assert all(u.instance_id != inst.instance_id for u in player.bench)


def test_move_to_board_and_back(gm):
    player = PlayerState(user_id=4)
    unit_sample = gm.data.units[0]
    inst = UnitInstance(unit_id=unit_sample.id)
    player.bench.append(inst)

    ok, msg = gm.move_to_board(player, inst.instance_id)
    assert ok
    assert any(u.instance_id == inst.instance_id for u in player.board)
    assert all(u.instance_id != inst.instance_id for u in player.bench)

    ok2, msg2 = gm.move_to_bench(player, inst.instance_id)
    assert ok2
    assert any(u.instance_id == inst.instance_id for u in player.bench)
    assert all(u.instance_id != inst.instance_id for u in player.board)


def test_try_auto_upgrade(gm):
    player = PlayerState(user_id=5)
    unit_sample = gm.data.units[0]
    # create three identical units
    for _ in range(3):
        player.bench.append(UnitInstance(unit_id=unit_sample.id, star_level=1))

    upgraded = gm.try_auto_upgrade(player, unit_sample.id, 1)
    assert upgraded is not None
    # upgraded should be star level 2
    assert upgraded == 2
    assert any(u.unit_id == unit_sample.id and u.star_level == 2 for u in player.bench)


def test_reroll_shop_insufficient_gold(gm):
    player = PlayerState(user_id=6)
    player.gold = 0
    ok, msg = gm.reroll_shop(player)
    assert not ok


def test_buy_xp_and_level_up(gm):
    player = PlayerState(user_id=7)
    player.gold = 100
    prev_level = player.level
    ok, msg = gm.buy_xp(player)
    assert ok
    assert player.gold == 96
    assert player.level >= prev_level


def test_get_board_synergies_returns_dict(gm):
    player = PlayerState(user_id=8)
    # board empty -> should return a dict (possibly empty)
    sy = gm.get_board_synergies(player)
    assert isinstance(sy, dict)
