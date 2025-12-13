import random
from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit


def make_unit(id, name, hp=100, attack=20, defense=10, attack_speed=1.0, effects=None):
    return CombatUnit(id=id, name=name, hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, effects=effects or [])


def test_simulate_basic_deterministic():
    random.seed(1)
    sim = CombatSimulator(dt=0.1, timeout=5)
    a = [make_unit("a1", "A1", hp=200, attack=30, defense=5, attack_speed=1.0)]
    b = [make_unit("b1", "B1", hp=120, attack=10, defense=2, attack_speed=0.8)]
    res = sim.simulate(a, b)
    assert isinstance(res, dict)
    assert res.get("winner") in ("team_a", "team_b")
    assert "duration" in res
    assert isinstance(res.get("log"), list)


def test_lifesteal_and_on_enemy_death_effects():
    random.seed(2)
    sim = CombatSimulator(dt=0.05, timeout=5)

    # Attacker has lifesteal and on_enemy_death buff
    effects_att = [
        {"type": "lifesteal", "value": 50},
        {"type": "on_enemy_death", "stats": ["attack"], "value": 5}
    ]
    a = [make_unit("a1", "Att", hp=150, attack=40, defense=5, attack_speed=1.2, effects=effects_att)]
    # Defender single weak unit
    b = [make_unit("b1", "Def", hp=30, attack=5, defense=1, attack_speed=0.5)]

    res = sim.simulate(a, b)
    log = res.get("log", [])
    # Expect some lifesteal log entries and on_enemy_death buff logs
    assert any("lifesteals" in entry for entry in log) or any("gains" in entry for entry in log)
    assert res["team_a_survivors"] >= 0


def test_per_round_buff_applies():
    random.seed(3)
    sim = CombatSimulator(dt=0.1, timeout=4)
    # Per-round buff increases attack each full second
    effects = [{"type": "per_round_buff", "stat": "attack", "value": 10, "is_percentage": False}]
    a = [make_unit("a1", "P1", hp=200, attack=20, defense=5, attack_speed=0.5, effects=effects)]
    b = [make_unit("b1", "E1", hp=150, attack=15, defense=3, attack_speed=0.6)]
    res = sim.simulate(a, b)
    log = res.get("log", [])
    assert any("per round" in entry for entry in log)
