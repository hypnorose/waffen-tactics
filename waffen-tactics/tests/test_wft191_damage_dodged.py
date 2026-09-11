from waffen_tactics.models.unit import Stats
from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit


def _unit(unit_id, name, hp, attack, attack_speed):
    stats = Stats(
        attack=attack,
        hp=hp,
        defense=0,
        max_mana=100,
        attack_speed=attack_speed,
        mana_on_attack=10,
    )
    return CombatUnit(
        id=unit_id,
        name=name,
        hp=hp,
        attack=attack,
        defense=0,
        attack_speed=attack_speed,
        max_mana=100,
        stats=stats,
    )


def test_wft191_dodge_emits_canonical_noop_without_ordinary_attack():
    attacker = _unit("player_1", "Attacker", hp=100, attack=40, attack_speed=100)
    target = _unit("opp_1", "Target", hp=100, attack=0, attack_speed=0)
    simulator = CombatSimulator(dt=0.1, timeout=0.25)
    simulator.passive_processor.damage_plan = lambda *args: {"dodged": True}
    events = []

    simulator.simulate(
        [attacker],
        [target],
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
        skip_per_round_buffs=True,
    )

    dodges = [payload for event_type, payload in events if event_type == "damage_dodged"]
    attacks = [payload for event_type, payload in events if event_type == "unit_attack"]

    assert dodges
    assert not attacks
    dodge = dodges[0]
    assert dodge["attacker_id"] == "player_1"
    assert dodge["attacker_name"] == "Attacker"
    assert dodge["unit_id"] == "opp_1"
    assert dodge["target_id"] == "opp_1"
    assert dodge["target_name"] == "Target"
    assert dodge["damage"] == 0
    assert dodge["applied_damage"] == 0
    assert dodge["pre_hp"] == 100
    assert dodge["post_hp"] == 100
    assert dodge["target_hp"] == 100
    assert dodge["post_shield"] == 0
    assert dodge["cause"] == "set2_dodge"
    assert target.hp == 100
    assert simulator.b_hp == [100]

