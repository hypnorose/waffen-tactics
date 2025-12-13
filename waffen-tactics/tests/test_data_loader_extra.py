from waffen_tactics.services.data_loader import build_stats_for_cost, build_skill_for_cost


def test_build_stats_for_cost_increases_with_cost():
    s1 = build_stats_for_cost(1)
    s5 = build_stats_for_cost(5)
    assert s5.attack > s1.attack
    assert s5.hp > s1.hp
    assert s5.defense >= s1.defense


def test_build_skill_for_cost_scaling():
    k1 = build_skill_for_cost(1)
    k5 = build_skill_for_cost(5)
    assert isinstance(k1.name, str)
    assert k5.effect.get('amount', 0) >= k1.effect.get('amount', 0)
