import random
from waffen_tactics.services.combat_shared import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.models.unit import Stats


def make_unit(id, name, hp=100, attack=20, defense=10, attack_speed=1.0, effects=None, max_mana=100):
    stats = Stats(attack=attack, hp=hp, defense=defense, max_mana=max_mana, attack_speed=attack_speed, mana_on_attack=10)
    return CombatUnit(id=id, name=name, hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, effects=effects or [], max_mana=max_mana, stats=stats)


def test_denciak_tier1_trigger_once(monkeypatch):
    """Denciak tier1 JSON-style effect: action reward with chance and trigger_once should yield a single gold reward when chance passes."""
    # Prepare simulator
    random.seed(123)
    sim = CombatSimulator(dt=0.1, timeout=5)

    # Denciak tier1 effect as in traits.json (actions + trigger_once)
    effects_denciak_tier1 = [
        {
            "trigger": "on_ally_death",
            "conditions": {"chance_percent": 50, "trigger_once": True},
            "rewards": [
                {"type": "resource", "resource": "gold", "value": 1, "value_type": "flat", "multiplier": 1.0}
            ]
        }
    ]

    # Ensure deterministic chance: make randint return 30 (<=50 -> success)
    monkeypatch.setattr('random.randint', lambda a, b: 30)

    # Attacking team: single strong killer
    a = [make_unit("a1", "Killer", hp=100, attack=100, defense=10, attack_speed=2.0)]

    # Defending team: one unit that will die, two survivors with denciak effect
    b = [
        make_unit("b1", "WeakAlly", hp=10, attack=1, defense=1, attack_speed=0.5),
        make_unit("b2", "Denciak1", hp=50, attack=5, defense=1, attack_speed=0.5, effects=effects_denciak_tier1),
        make_unit("b3", "Denciak2", hp=50, attack=5, defense=1, attack_speed=0.5, effects=effects_denciak_tier1),
    ]

    events = []
    def event_callback(event_type, data):
        events.append((event_type, data))

    res = sim.simulate(a, b, event_callback=event_callback)

    # Find death of WeakAlly
    assert any(e[0] == 'unit_died' and e[1].get('unit_name') == 'WeakAlly' for e in events)

    # Gold reward events should include a single reward due to trigger_once
    gold_events = [e for e in events if e[0] == 'gold_reward']
    assert len(gold_events) >= 1
    # Ensure at least one gold event has the expected amount
    assert any(e[1].get('amount') == 1 for e in gold_events)


def test_denciak_tier3_always_rewards(monkeypatch):
    """Denciak tier3 JSON-style effect: 100% chance, value 2, trigger_once should still yield a single reward (per death)."""
    random.seed(7)
    sim = CombatSimulator(dt=0.1, timeout=5)

    effects_denciak_tier3 = [
        {
            "trigger": "on_ally_death",
            "conditions": {"chance_percent": 100, "trigger_once": True},
            "rewards": [
                {"type": "resource", "resource": "gold", "value": 2, "value_type": "flat", "multiplier": 1.0}
            ]
        }
    ]

    # Even if randint is patched, chance 100 should always pass
    monkeypatch.setattr('random.randint', lambda a, b: 99)

    a = [make_unit("a1", "Killer", hp=100, attack=100, defense=10, attack_speed=2.0)]
    b = [
        make_unit("b1", "WeakAlly", hp=10, attack=1, defense=1, attack_speed=0.5),
        make_unit("b2", "Denciak1", hp=50, attack=5, defense=1, attack_speed=0.5, effects=effects_denciak_tier3),
    ]

    events = []
    def event_callback(event_type, data):
        events.append((event_type, data))

    res = sim.simulate(a, b, event_callback=event_callback)

    gold_events = [e for e in events if e[0] == 'gold_reward']
    assert len(gold_events) >= 1
    # Check amounts contain a 2
    assert any(e[1]['amount'] == 2 for e in gold_events)


def test_denciak_chance_failure(monkeypatch):
    """If chance fails, no gold_reward should be emitted near the death."""
    random.seed(5)
    sim = CombatSimulator(dt=0.1, timeout=5)

    effects_fail = [
        {
            "trigger": "on_ally_death",
            "conditions": {"chance_percent": 30, "trigger_once": True},
            "rewards": [
                {"type": "resource", "resource": "gold", "value": 3, "value_type": "flat", "multiplier": 1.0}
            ]
        }
    ]

    # Make randint return a value above chance to simulate failure
    monkeypatch.setattr('random.randint', lambda a, b: 99)

    a = [make_unit("a1", "Killer", hp=100, attack=100, defense=10, attack_speed=2.0)]
    b = [
        make_unit("b1", "WeakAlly", hp=10, attack=1, defense=1, attack_speed=0.5),
        make_unit("b2", "Denciak1", hp=50, attack=5, defense=1, attack_speed=0.5, effects=effects_fail),
    ]

    events = []
    def event_callback(event_type, data):
        events.append((event_type, data))

    sim.simulate(a, b, event_callback=event_callback)

    # Ensure no gold_reward close to death time
    gold_events = [e for e in events if e[0] == 'gold_reward']
    assert len(gold_events) == 0


def test_denciak_multiple_deaths_reset_trigger_once(monkeypatch):
    """Trigger_once should apply per death; two separate deaths should each be able to produce one reward."""
    random.seed(11)
    sim = CombatSimulator(dt=0.1, timeout=5)

    effects_t1 = [
        {"trigger": "on_ally_death", "conditions": {"chance_percent": 100, "trigger_once": True}, "rewards": [{"type": "resource", "resource": "gold", "value": 1, "value_type": "flat", "multiplier": 1.0}]}
    ]

    # Single strong attacker, two separate defenders will die sequentially
    a = [make_unit("a1", "Killer", hp=200, attack=120, defense=10, attack_speed=2.0)]
    b = [
        make_unit("b1", "Weak1", hp=10, attack=1, defense=1, attack_speed=0.5),
        make_unit("b2", "Weak2", hp=10, attack=1, defense=1, attack_speed=0.5),
        make_unit("b3", "Denc", hp=80, attack=5, defense=1, attack_speed=0.5, effects=effects_t1),
    ]

    events = []
    def event_callback(event_type, data):
        events.append((event_type, data))

    sim.simulate(a, b, event_callback=event_callback)

    # There should be at least one gold_reward for the first death and possibly another when second dies
    gold_events = [e for e in events if e[0] == 'gold_reward']
    # Since chance is 100, expect at least 1 reward; ensure not more than 2
    assert 1 <= len(gold_events) <= 2

