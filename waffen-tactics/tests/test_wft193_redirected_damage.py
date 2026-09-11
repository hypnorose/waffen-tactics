"""WFT-193 regression coverage for the explicit Haxball redirect event."""

from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit


def _unit(unit_id, name, hp, attack, attack_speed, *, effects=None, traits=None):
    return CombatUnit(
        unit_id,
        name,
        hp,
        attack,
        0,
        attack_speed,
        effects=effects,
        traits=traits,
    )


def _haxball_effect():
    return {
        "set2_trait": "Haxball",
        "set2_tier": 1,
        "set2_value": 40,
        "set2_trait_owner": True,
    }


def test_haxball_redirect_emits_damage_then_unit_died_with_authoritative_state(monkeypatch):
    monkeypatch.setenv("WAFFEN_DETERMINISTIC_TARGETING", "1")
    effect = _haxball_effect()
    attacker = _unit("attacker", "Attacker", 100, 50, 100)
    target = _unit("target", "Target", 100, 10, 0, effects=[effect], traits=["Haxball"])
    redirected = _unit("redirected", "Redirected", 8, 10, 0, effects=[effect], traits=["Haxball"])
    events = []

    CombatSimulator(dt=0.1, timeout=0.25).simulate(
        [attacker],
        [target, redirected],
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
        skip_per_round_buffs=True,
    )

    redirect_index = next(i for i, (event_type, _) in enumerate(events) if event_type == "damage")
    death_index = next(i for i, (event_type, payload) in enumerate(events) if event_type == "unit_died" and payload.get("unit_id") == "redirected")
    event_type, redirect = events[redirect_index]

    assert event_type == "damage"
    assert redirect["event_id"]
    assert redirect["seq"] < events[death_index][1]["seq"]
    assert redirect["attacker_id"] == "attacker"
    assert redirect["target_id"] == "redirected"
    assert redirect["cause"] == "set2_haxball_redirect"
    assert redirect["damage"] == redirect["applied_damage"] == 20
    assert redirect["pre_hp"] == 8
    assert redirect["post_hp"] == redirect["target_hp"] == 0
    assert redirect["post_shield"] == 0
    assert redirected.hp == 0


def test_attack_without_haxball_redirect_remains_unit_attack(monkeypatch):
    monkeypatch.delenv("WAFFEN_DETERMINISTIC_TARGETING", raising=False)
    attacker = _unit("attacker", "Attacker", 100, 20, 100)
    target = _unit("target", "Target", 100, 0, 0)
    events = []

    CombatSimulator(dt=0.1, timeout=0.15).simulate(
        [attacker],
        [target],
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
        skip_per_round_buffs=True,
    )

    assert any(event_type == "unit_attack" for event_type, _ in events)
    assert not any(event_type == "damage" for event_type, _ in events)
