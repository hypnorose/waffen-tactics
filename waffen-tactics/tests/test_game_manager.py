import pytest
from collections import Counter

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


@pytest.mark.parametrize("location", ["bench", "board"])
def test_sell_unit_returns_equipped_items(gm, location):
    player = PlayerState(user_id=30)
    unit_sample = gm.data.units[0]
    equipped_items = ["spices", "orangeade", "plaszcz_200_welny"]
    inst = UnitInstance(unit_id=unit_sample.id, items=equipped_items)
    getattr(player, location).append(inst)

    ok, _ = gm.sell_unit(player, inst.instance_id)

    assert ok
    assert player.item_inventory[-len(equipped_items):] == equipped_items
    assert inst not in getattr(player, location)


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


def test_invalid_position_is_rejected_without_mutating_bench_or_board(gm):
    player = PlayerState(user_id=40)
    unit_sample = gm.data.units[0]
    inst = UnitInstance(unit_id=unit_sample.id, position='front')
    player.bench.append(inst)

    ok, message = gm.move_to_board(player, inst.instance_id, 'middle')

    assert not ok
    assert 'Nieprawidłowa pozycja' in message
    assert player.bench == [inst]
    assert player.board == []
    assert inst.position == 'front'


def test_invalid_switch_position_is_rejected_without_mutating_board(gm):
    player = PlayerState(user_id=41)
    unit_sample = gm.data.units[0]
    inst = UnitInstance(unit_id=unit_sample.id, position='front')
    player.board.append(inst)

    ok, message = gm.switch_line(player, inst.instance_id, 'middle')

    assert not ok
    assert 'Nieprawidłowa pozycja' in message
    assert player.board == [inst]
    assert inst.position == 'front'


def test_invalid_persisted_position_is_rejected_at_state_boundary():
    with pytest.raises(ValueError, match='Unsupported unit position'):
        PlayerState.from_dict({
            'user_id': 42,
            'board': [{'unit_id': 'unit_001', 'star_level': 1, 'position': 'middle'}],
        })


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


@pytest.mark.parametrize('item_count', range(7))
def test_try_auto_upgrade_preserves_all_items_and_overflows_after_three(gm, item_count):
    player = PlayerState(user_id=50 + item_count, item_inventory=[])
    unit_id = gm.data.units[0].id
    source_items = ['spices', 'safe', 'coat', 'socks', 'notebook', 'orangeade']
    cursor = 0
    for source_index in range(3):
        item_slice = source_items[cursor:min(cursor + 3, item_count)]
        cursor = min(cursor + 3, item_count)
        player.bench.append(
            UnitInstance(
                unit_id=unit_id,
                star_level=1,
                instance_id=f'source-{item_count}-{source_index}',
                items=item_slice,
            )
        )

    upgraded = gm.try_auto_upgrade(player, unit_id, 1)

    assert upgraded == 2
    result = next(unit for unit in player.bench if unit.star_level == 2)
    assert result.items == source_items[:item_count][:3]
    assert player.item_inventory == source_items[:item_count][3:]
    assert Counter(result.items + player.item_inventory) == Counter(source_items[:item_count])


def test_try_auto_upgrade_rolls_back_all_state_when_upgrade_creation_fails(gm, monkeypatch):
    import waffen_tactics.services.unit_manager as unit_manager_module

    player = PlayerState(user_id=57, item_inventory=['notebook'])
    unit_id = gm.data.units[0].id
    sources = [
        UnitInstance(unit_id=unit_id, star_level=1, instance_id='rollback-1', items=['spices']),
        UnitInstance(unit_id=unit_id, star_level=1, instance_id='rollback-2', items=['safe']),
        UnitInstance(unit_id=unit_id, star_level=1, instance_id='rollback-3', items=['coat']),
    ]
    player.bench.extend(sources)
    original_bench = list(player.bench)
    original_board = list(player.board)
    original_inventory = list(player.item_inventory)

    def fail_creation(*args, **kwargs):
        raise RuntimeError('simulated merge failure')

    monkeypatch.setattr(unit_manager_module, 'UnitInstance', fail_creation)

    with pytest.raises(RuntimeError, match='simulated merge failure'):
        gm.try_auto_upgrade(player, unit_id, 1)

    assert player.bench == original_bench
    assert player.board == original_board
    assert player.item_inventory == original_inventory


def test_try_auto_upgrade_logs_item_ownership_and_overflow(gm, caplog):
    player = PlayerState(user_id=58, item_inventory=[])
    unit_id = gm.data.units[0].id
    for index, item_ids in enumerate((['spices', 'safe'], ['coat'], ['socks'])):
        player.bench.append(
            UnitInstance(
                unit_id=unit_id,
                star_level=1,
                instance_id=f'log-{index}',
                items=item_ids,
            )
        )

    with caplog.at_level('INFO', logger='waffen_tactics'):
        gm.try_auto_upgrade(player, unit_id, 1)

    assert 'overflow_items' in caplog.text
    assert "all_item_ids=['spices', 'safe', 'coat', 'socks']" in caplog.text
    assert "['socks']" in caplog.text
    assert 'state_before=' in caplog.text
    assert 'state_after=' in caplog.text
    assert 'overflow_destination=item_inventory' in caplog.text


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
