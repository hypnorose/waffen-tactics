import pytest

from waffen_tactics.models.unit import Stats
from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.event_canonicalizer import emit_damage, emit_stat_buff
from waffen_tactics.services.passive_definitions import get_passive_definition
from waffen_tactics.services.passive_processor import PassiveProcessor


def make_unit(unit_id, passive_id=None, *, hp=1000, attack=20, defense=0, attack_speed=2.0, max_mana=100, position="front", star_level=1):
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
        star_level=star_level,
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


class FailingDotPopList(list):
    def pop(self, index=-1):
        raise RuntimeError("DoT removal rejected")


def test_dot_expiration_removal_failure_fails_closed_without_expired_event():
    sim = CombatSimulator(dt=0.1, timeout=1)
    unit = make_unit("dot_failure", hp=100, attack_speed=0.0)
    dot = {
        "id": "dot-failure",
        "type": "damage_over_time",
        "damage": 10,
        "damage_type": "poison",
        "interval": 1.0,
        "ticks_remaining": 1,
        "total_ticks": 1,
        "next_tick_time": 0.0,
    }
    unit.effects = FailingDotPopList([dot])
    events = []

    with pytest.raises(RuntimeError, match="Failed to remove expired DoT"):
        sim._process_dot_for_team(
            [unit],
            hp_list=[100],
            time=1.0,
            log=[],
            event_callback=lambda event_type, payload: events.append((event_type, payload)),
            side="team_a",
        )

    assert unit.hp == 90
    assert unit.effects == [dot]
    assert not any(event_type == "damage_over_time_expired" for event_type, _ in events)


def test_dot_expiration_removes_only_expired_effect_and_emits_event():
    sim = CombatSimulator(dt=0.1, timeout=1)
    unit = make_unit("dot_valid", hp=100, attack_speed=0.0)
    expired = {
        "id": "dot-expired",
        "type": "damage_over_time",
        "damage": 10,
        "damage_type": "poison",
        "interval": 1.0,
        "ticks_remaining": 1,
        "total_ticks": 1,
        "next_tick_time": 0.0,
    }
    future = {
        "id": "dot-future",
        "type": "damage_over_time",
        "damage": 4,
        "damage_type": "magic",
        "interval": 1.0,
        "ticks_remaining": 2,
        "total_ticks": 2,
        "next_tick_time": 2.0,
    }
    unit.effects = [expired, future]
    events = []

    sim._process_dot_for_team(
        [unit],
        hp_list=[100],
        time=1.0,
        log=[],
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
        side="team_a",
    )

    assert unit.hp == 90
    assert unit.effects == [future]
    expiration_events = [
        payload for event_type, payload in events
        if event_type == "damage_over_time_expired"
    ]
    assert len(expiration_events) == 1
    assert expiration_events[0]["effect_id"] == "dot-expired"


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


def test_passive_trigger_event_carries_authoritative_display_name():
    unit = make_unit("named_passive")
    unit.passive = {"name": "Jajcarz", "description": "Stunuje po bonus attacku."}
    events = []

    PassiveProcessor()._emit(lambda event_type, payload: events.append((event_type, payload)), unit, "on_bonus_attack", "passive_ready", "team_a", 1.25)

    assert events[0][0] == "passive_triggered"
    assert events[0][1]["passive_name"] == "Jajcarz"
    assert events[0][1]["description"] == "Stunuje po bonus attacku."


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


def test_passive_strength_scales_by_star_level():
    processor = PassiveProcessor()
    unit = make_unit("scaling", hp=1000, star_level=1)
    assert processor._scaled_value(unit, 10) == 10
    unit = make_unit("scaling", hp=1000, star_level=2)
    assert processor._scaled_value(unit, 10) == 15
    unit = make_unit("scaling", hp=1000, star_level=3)
    assert processor._scaled_value(unit, 10) == 20


def test_krasu_bonus_attack_is_five_percent_base():
    definition = get_passive_definition("krasu")

    assert definition["value"] == 5
    assert definition["effect"] == "all_secondary"


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


def test_expired_hp_effect_uses_canonical_hp_mutation():
    unit = make_unit("hp-expiry", hp=110, attack_speed=0.0)
    unit.effects = [{
        "id": "hp-expiry-effect",
        "type": "buff",
        "stat": "hp",
        "applied_delta": 10,
        "expires_at": 1.0,
    }]
    events = []

    CombatSimulator()._process_effect_expiration_for_team(
        [unit],
        [unit.hp],
        time=1.0,
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
        side="team_a",
    )

    assert unit.hp == 100
    assert unit.max_hp == 110
    assert unit.effects == []
    expiration = next(payload for event_type, payload in events if event_type == "effect_expired")
    assert expiration["post_hp"] == 100
    assert expiration["post_hp"] == expiration["unit_hp"]


def test_expired_max_hp_effect_uses_canonical_mutation_and_preserves_ratio():
    unit = make_unit("max-hp-expiry", hp=100, attack_speed=0.0)
    emit_stat_buff(None, unit, "max_hp", 20, duration=1.0, timestamp=0.0)
    emit_damage(None, None, unit, raw_damage=24, emit_event=False)
    events = []

    CombatSimulator()._process_effect_expiration_for_team(
        [unit],
        [unit.hp],
        time=1.0,
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
        side="team_a",
    )

    assert unit.max_hp == 100
    assert unit.hp == 80
    assert unit.effects == []
    expiration = next(payload for event_type, payload in events if event_type == "effect_expired")
    assert expiration["post_max_hp"] == 100
    assert expiration["post_hp"] == 80


def test_effect_expiration_fails_before_mutation_when_collection_is_malformed():
    unit = make_unit("malformed-expiry", hp=100, attack_speed=0.0)
    expired_effect = {
        "id": "shield-expiry-effect",
        "type": "shield",
        "applied_amount": 3,
        "expires_at": 1.0,
    }
    unit._state.effects = [expired_effect, "malformed-effect"]
    unit.shield = 3
    events = []

    with pytest.raises(RuntimeError, match="Cannot prepare expiration removal"):
        CombatSimulator()._process_effect_expiration_for_team(
            [unit],
            [unit.hp],
            time=1.0,
            event_callback=lambda event_type, payload: events.append((event_type, payload)),
            side="team_a",
        )

    assert unit.shield == 3
    assert unit._state.effects == [expired_effect, "malformed-effect"]
    assert events == []


def test_attack_counter_passive_emits_one_trigger_and_keeps_basic_attack_order():
    counter = make_unit("falconbalkon", "falconbalkon", max_mana=100, attack_speed=2.0)
    target = make_unit("target", hp=5000, attack_speed=0.0)

    _, events = run([counter], [target], timeout=1.8)

    passive_events = [payload for event_type, payload in events if event_type == "passive_triggered"]
    assert any(payload.get("effect") == "mana_self" for payload in passive_events)
    assert all(event_type != "skill_cast" for event_type, _ in events)
    attack_seq = [payload.get("seq") for event_type, payload in events if event_type == "unit_attack"]
    assert attack_seq == sorted(attack_seq)


def test_passive_effect_collection_mutations_emit_canonical_apply_events():
    processor = PassiveProcessor()
    target = make_unit("target", hp=5000, attack_speed=0.0)

    owner = make_unit("mrvlook", "mrvlook", attack_speed=0.0)
    events = []
    processor.initialize([owner], [target], lambda event_type, payload: events.append((event_type, payload)), timestamp=0.0)
    applied = [payload for event_type, payload in events if event_type == "effect_applied"]
    assert len(applied) == 1
    assert applied[0]["effect"]["type"] == "damage_reduction"
    assert applied[0]["effect"]["id"] == applied[0]["effect_id"]

    owner = make_unit("socjopata", "socjopata", attack_speed=0.0)
    events = []
    processor.bonus_attack_plan(owner, target, [owner], [target], lambda event_type, payload: events.append((event_type, payload)), "team_a", 1.0)
    applied = [payload for event_type, payload in events if event_type == "effect_applied"]
    assert len(applied) == 1
    assert applied[0]["effect"]["type"] == "mana_lock"
    assert applied[0]["effect"]["expires_at"] == 3.0

    owner = make_unit("flaminga", "flaminga", attack_speed=0.0)
    events = []
    processor.bonus_attack_plan(owner, target, [owner], [target], lambda event_type, payload: events.append((event_type, payload)), "team_a", 1.0)
    applied = [payload for event_type, payload in events if event_type == "effect_applied"]
    assert len(applied) == 1
    assert applied[0]["effect"]["type"] == "damage_over_time"
    assert applied[0]["effect"]["expires_at"] == 4.0


def test_rafcikd_threshold_damage_reduction_expires_with_its_shield():
    unit = make_unit("rafcikd", "rafcikd", hp=1000, attack_speed=0.0)
    processor = PassiveProcessor()
    events = []

    processor.after_damage(
        unit,
        old_hp=600,
        new_hp=490,
        team=[unit],
        enemies=[],
        callback=lambda event_type, payload: events.append((event_type, payload)),
        side="team_a",
        timestamp=1.0,
    )

    reduction = next(effect for effect in unit.effects if effect.get("type") == "damage_reduction")
    shield = next(effect for effect in unit.effects if effect.get("type") == "shield")
    assert reduction["duration"] == 4
    assert reduction["expires_at"] == 5.0
    assert shield["duration"] == 4
    assert shield["expires_at"] == 5.0
    assert unit.damage_reduction == 20

    CombatSimulator()._process_effect_expiration_for_team(
        [unit],
        [unit.hp],
        time=5.0,
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
        side="team_a",
    )

    assert not unit.effects
    assert unit.damage_reduction == 0
    expirations = [payload for event_type, payload in events if event_type == "effect_expired"]
    assert len(expirations) == 2
    assert {payload["effect_type"] for payload in expirations} == {"damage_reduction", "shield"}


def test_replacing_passive_effect_emits_expiration_before_new_application():
    unit = make_unit("replaceable")
    events = []

    PassiveProcessor._append_effect(
        unit,
        {"id": "old-effect", "type": "mana_lock", "source": "caster", "passive_effect": "mana_lock"},
        lambda event_type, payload: events.append((event_type, payload)),
        "team_a",
        1.0,
    )
    PassiveProcessor._append_effect(
        unit,
        {"id": "new-effect", "type": "mana_lock", "source": "caster", "passive_effect": "mana_lock"},
        lambda event_type, payload: events.append((event_type, payload)),
        "team_a",
        2.0,
    )

    assert [event_type for event_type, _ in events] == [
        "effect_applied", "effect_expired", "effect_applied"
    ]
    assert unit.effects == [{"id": "new-effect", "type": "mana_lock", "source": "caster", "passive_effect": "mana_lock"}]
