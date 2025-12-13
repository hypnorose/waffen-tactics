import random
from waffen_tactics.services.shop import ShopService
from waffen_tactics.models.unit import Unit, Stats, Skill


def make_unit(uid, cost):
    stats = Stats(attack=40, hp=420, defense=12, max_mana=100, attack_speed=0.8)
    skill = Skill(name="s", description="d", mana_cost=100, effect={})
    return Unit(id=uid, name=f"U{uid}", cost=cost, factions=[], classes=[], stats=stats, skill=skill)


def test_shop_roll_level_1_returns_cost_1_units():
    # For level 1, odds map only cost 1
    units = [make_unit("u1", 1), make_unit("u2", 1), make_unit("u3", 2), make_unit("u4", 2)]
    shop = ShopService(units)
    random.seed(5)
    offers = shop.roll(level=1, count=5)
    assert len(offers) == 5
    assert all(getattr(u, 'cost', None) == 1 for u in offers)


def test_shop_roll_returns_requested_count():
    units = [make_unit("a",1), make_unit("b",2), make_unit("c",3)]
    shop = ShopService(units)
    random.seed(7)
    offers = shop.roll(level=3, count=3)
    assert len(offers) == 3
