import random
from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit
from waffen_tactics.models.unit import Stats


def make_unit(id, name, hp=100, attack=20, defense=10, attack_speed=1.0, effects=None, max_mana=100):
    stats = Stats(attack=attack, hp=hp, defense=defense, max_mana=max_mana, attack_speed=attack_speed, mana_on_attack=10)
    return CombatUnit(id=id, name=name, hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, effects=effects or [], max_mana=max_mana, stats=stats)


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


def test_on_enemy_death_event_callback():
    """Test that on_enemy_death effects send stat_buff events via callback"""
    random.seed(42)
    sim = CombatSimulator(dt=0.1, timeout=10)

    # Attacker has on_enemy_death buff (like Streamer)
    effects_att = [
        {"type": "on_enemy_death", "stats": ["attack", "defense"], "value": 2}
    ]
    a = [make_unit("a1", "StreamerUnit", hp=100, attack=50, defense=10, attack_speed=1.0, effects=effects_att)]
    # Defender weak unit that will die
    b = [make_unit("b1", "WeakDef", hp=20, attack=5, defense=1, attack_speed=0.5)]

    events = []
    def event_callback(event_type, data):
        events.append((event_type, data))

    res = sim.simulate(a, b, event_callback=event_callback)
    
    print("Events:", events)
    print("Log:", res.get("log", []))
    
    # Check that unit died
    assert any(e[0] == 'unit_died' for e in events)
    
    # Check that stat_buff events were sent
    stat_buff_events = [e for e in events if e[0] == 'stat_buff']
    assert len(stat_buff_events) >= 2  # At least attack and defense buffs
    
    # Check specific buffs
    attack_buffs = [e for e in stat_buff_events if e[1]['stat'] == 'attack']
    defense_buffs = [e for e in stat_buff_events if e[1]['stat'] == 'defense']
    
    assert len(attack_buffs) >= 1
    assert len(defense_buffs) >= 1
    
    # Check values
    assert attack_buffs[0][1]['amount'] == 2
    assert defense_buffs[0][1]['amount'] == 2
    
    # Check unit name
    assert attack_buffs[0][1]['unit_name'] == 'StreamerUnit'


def test_on_ally_death_trigger_once():
    """Test that on_ally_death with trigger_once sends gold_reward only once per death event"""
    random.seed(42)
    sim = CombatSimulator(dt=0.1, timeout=10)

    # Two units with on_ally_death gold reward (like Denciak)
    effects_denciak = [
        {"type": "on_ally_death", "reward": "gold", "value": 2, "trigger_once": True}
    ]
    # Attacking team: one strong unit
    a = [make_unit("a1", "Killer", hp=100, attack=100, defense=10, attack_speed=2.0)]
    # Defending team: one weak unit that dies, two survivors with gold reward effect
    b = [
        make_unit("b1", "WeakAlly", hp=10, attack=1, defense=1, attack_speed=0.5),  # Dies
        make_unit("b2", "Denciak1", hp=50, attack=5, defense=1, attack_speed=0.5, effects=effects_denciak),  # Survives
        make_unit("b3", "Denciak2", hp=50, attack=5, defense=1, attack_speed=0.5, effects=effects_denciak)   # Survives
    ]

    events = []
    def event_callback(event_type, data):
        events.append((event_type, data))

    res = sim.simulate(a, b, event_callback=event_callback)

    print("Events:", events)
    print("Log:", res.get("log", []))

    # Check that WeakAlly died
    unit_died_events = [e for e in events if e[0] == 'unit_died']
    weak_ally_died = any(e[1]['unit_name'] == 'WeakAlly' for e in unit_died_events)
    assert weak_ally_died

    # Check gold_reward events - should be only 1 due to trigger_once for the WeakAlly death
    gold_reward_events = [e for e in events if e[0] == 'gold_reward' and abs(e[1]['timestamp'] - 0.3) < 0.1]  # Only rewards around WeakAlly death time
    assert len(gold_reward_events) == 1  # Only one reward per death event due to trigger_once

    # Check the reward amount
    assert gold_reward_events[0][1]['amount'] == 2


def test_on_ally_death_without_trigger_once():
    """Test that on_ally_death without trigger_once sends gold_reward for each surviving unit"""
    random.seed(42)
    sim = CombatSimulator(dt=0.1, timeout=10)

    # Two units with on_ally_death gold reward but WITHOUT trigger_once
    effects_denciak_no_trigger = [
        {"type": "on_ally_death", "reward": "gold", "value": 2}  # No trigger_once
    ]
    # Attacking team: one strong unit
    a = [make_unit("a1", "Killer", hp=100, attack=100, defense=10, attack_speed=2.0)]
    # Defending team: one weak unit that dies, two survivors with gold reward effect
    b = [
        make_unit("b1", "WeakAlly", hp=10, attack=1, defense=1, attack_speed=0.5),  # Dies
        make_unit("b2", "Denciak1", hp=50, attack=5, defense=1, attack_speed=0.5, effects=effects_denciak_no_trigger),  # Survives
        make_unit("b3", "Denciak2", hp=50, attack=5, defense=1, attack_speed=0.5, effects=effects_denciak_no_trigger)   # Survives
    ]

    events = []
    def event_callback(event_type, data):
        events.append((event_type, data))

    res = sim.simulate(a, b, event_callback=event_callback)

    print("Events:", events)
    print("Log:", res.get("log", []))

    # Check that WeakAlly died
    unit_died_events = [e for e in events if e[0] == 'unit_died']
    weak_ally_died = any(e[1]['unit_name'] == 'WeakAlly' for e in unit_died_events)
    assert weak_ally_died

    # Check gold_reward events - should be 2 (one for each surviving unit with effect)
    gold_reward_events = [e for e in events if e[0] == 'gold_reward' and abs(e[1]['timestamp'] - 0.3) < 0.1]  # Only rewards around WeakAlly death time
    assert len(gold_reward_events) == 2  # Two rewards without trigger_once

    # Check the reward amounts
    amounts = [e[1]['amount'] for e in gold_reward_events]
    assert amounts == [2, 2]


def test_per_round_buff_applies():
    random.seed(3)
    sim = CombatSimulator(dt=0.1, timeout=4)
    # Per-round buff increases attack each full second
    effects = [{"type": "per_second_buff", "stat": "attack", "value": 10, "is_percentage": False}]
    a = [make_unit("a1", "P1", hp=200, attack=20, defense=5, attack_speed=0.5, effects=effects)]
    b = [make_unit("b1", "E1", hp=150, attack=15, defense=3, attack_speed=0.6)]
    res = sim.simulate(a, b)
    log = res.get("log", [])
    assert any("per second" in entry for entry in log)
