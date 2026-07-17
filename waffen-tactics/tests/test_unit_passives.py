from waffen_tactics.models.unit import Stats
from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.event_canonicalizer import emit_damage
from waffen_tactics.services.passive_definitions import get_passive_definition


def make_unit(unit_id, passive_id=None, *, hp=1000, attack=20, defense=0, attack_speed=2.0, max_mana=100, position="front"):
    stats = Stats(
        attack=attack,
        hp=hp,
        defense=defense,
        max_mana=max_mana,
        attack_speed=attack_speed,
        mana_on_attack=10,
        mana_regen=0,
    )
    return CombatUnit(
        id=unit_id,
        name=unit_id,
        hp=hp,
        attack=attack,
        defense=defense,
        attack_speed=attack_speed,
        max_mana=max_mana,
        stats=stats,
        position=position,
        passive=get_passive_definition(passive_id) if passive_id else None,
    )


def run(team_a, team_b, timeout=2):
    events = []
    result = CombatSimulator(dt=0.1, timeout=timeout).simulate(
        team_a,
        team_b,
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
    )
    return result, events


def test_every_loaded_unit_has_one_passive_definition():
    units = load_game_data().units
    assert len(units) == 52
    assert all(unit.passive and unit.passive.get("description") for unit in units)


def test_position_passive_changes_the_starting_mode_without_skill_cast():
    front = make_unit("front_kubica", "kubica", attack=100, attack_speed=1.0, position="front")
    back = make_unit("back_kubica", "kubica", attack=100, attack_speed=1.0, position="back")
    target = make_unit("target", hp=100000, attack_speed=0.0)

    _, front_events = run([front], [target], timeout=0.01)
    _, back_events = run([back], [target], timeout=0.01)

    assert front.attack == 115
    assert back.attack_speed == 1.15
    assert all(event_type != "skill_cast" for event_type, _ in front_events + back_events)
    assert any(payload.get("effect") == "passive_ready" for event_type, payload in front_events if event_type == "passive_triggered")


def test_full_mana_bonus_attack_can_feed_team_mana_without_skill_cast():
    caster = make_unit("yossarian", "yossarian", max_mana=20, attack_speed=2.0)
    ally = make_unit("ally", max_mana=100, attack_speed=2.0)
    target = make_unit("target", hp=5000, attack_speed=0.0)

    _, events = run([caster, ally], [target], timeout=2)

    bonus_attacks = [payload for event_type, payload in events if event_type == "unit_attack" and payload.get("bonus_attack")]
    assert bonus_attacks
    assert any(
        event_type == "passive_triggered" and payload.get("effect") == "team_mana"
        for event_type, payload in events
    )
    assert all(event_type != "skill_cast" for event_type, _ in events)


def test_dumb_lowest_hp_preference_is_bonus_attack_only():
    definition = get_passive_definition("dumb")

    assert definition["kind"] == "start_target_bonus"
    assert definition["preference"] == "lowest_hp"
    assert "dodatkowy atak" in definition["description"]


def test_hyodo_max_hp_passive_preserves_current_health_ratio():
    hyodo = make_unit("hyodo888", "hyodo888", hp=1000, attack_speed=0.0)
    target = make_unit("target", hp=100000, attack_speed=0.0)

    _, events = run([hyodo], [target], timeout=0.01)

    stat_events = [payload for event_type, payload in events if event_type == "stat_buff" and payload.get("unit_id") == "hyodo888"]
    assert len(stat_events) == 1
    event = stat_events[0]
    assert event["stat"] == "max_hp"
    assert event["value_type"] == "percentage"
    assert event["applied_delta"] == 100
    assert event["pre_hp"] == 1000
    assert event["post_hp"] == 1100
    assert hyodo.max_hp == 1100
    assert hyodo.hp == 1100


def test_hyodo_max_hp_passive_scales_damaged_health_by_the_same_ratio():
    hyodo = make_unit("hyodo888", "hyodo888", hp=1000, attack_speed=0.0)
    emit_damage(None, None, hyodo, raw_damage=500, emit_event=False)
    target = make_unit("target", hp=100000, attack_speed=0.0)

    _, events = run([hyodo], [target], timeout=0.01)

    stat_event = next(payload for event_type, payload in events if event_type == "stat_buff" and payload.get("unit_id") == "hyodo888")
    assert stat_event["pre_hp"] == 500
    assert stat_event["post_hp"] == 550
    assert hyodo.max_hp == 1100
    assert hyodo.hp == 550


def test_attack_counter_passive_emits_one_trigger_and_keeps_basic_attack_order():
    counter = make_unit("falconbalkon", "falconbalkon", max_mana=100, attack_speed=2.0)
    target = make_unit("target", hp=5000, attack_speed=0.0)

    _, events = run([counter], [target], timeout=1.8)

    passive_events = [payload for event_type, payload in events if event_type == "passive_triggered"]
    assert any(payload.get("effect") == "mana_self" for payload in passive_events)
    assert all(event_type != "skill_cast" for event_type, _ in events)
    attack_seq = [payload.get("seq") for event_type, payload in events if event_type == "unit_attack"]
    assert attack_seq == sorted(attack_seq)
