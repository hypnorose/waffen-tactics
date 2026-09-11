from waffen_tactics.models.unit import Stats
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.passive_processor import PassiveProcessor


def _unit(unit_id, passive=None, *, position="front", hp=1000, attack_speed=1.0, mana_on_attack=10):
    stats = Stats(
        attack=20,
        hp=hp,
        defense=5,
        max_mana=100,
        attack_speed=attack_speed,
        mana_on_attack=mana_on_attack,
        mana_regen=0,
    )
    return CombatUnit(
        id=unit_id,
        name=unit_id,
        hp=hp,
        attack=20,
        defense=5,
        attack_speed=attack_speed,
        max_mana=100,
        stats=stats,
        position=position,
        passive=passive,
    )


def test_swap_enemy_line_emits_one_explicit_transition_before_passive_metadata():
    owner = _unit(
        "e7e66be4",
        {
            "id": "set2.passive.yossarian",
            "name": "Yossarian",
            "effect": "swap_enemy_line",
            "runtime": {"type": "swap_enemy_line"},
        },
        position="back",
    )
    enemies = [_unit("opp_1"), _unit("opp_2")]
    events = []

    PassiveProcessor().bonus_attack_plan(
        owner,
        enemies[0],
        [owner],
        enemies,
        lambda event_type, payload: events.append((event_type, payload)),
        "team_a",
        3.75,
    )

    formation_events = [payload for event_type, payload in events if event_type == "formation_changed"]
    assert len(formation_events) == 1
    formation = formation_events[0]
    assert formation["previous_position"] == "front"
    assert formation["new_position"] == "back"
    assert formation["source_id"] == owner.id
    assert formation["passive_id"] == "set2.passive.yossarian"
    assert formation["cause"] == "swap_enemy_line"
    assert events.index(("formation_changed", formation)) < next(
        index for index, (event_type, payload) in enumerate(events)
        if event_type == "passive_triggered" and payload.get("effect") == "swap_enemy_line"
    )
    changed_target = next(enemy for enemy in enemies if enemy.id == formation["unit_id"])
    assert changed_target.position == "back"


def test_ordinary_attack_path_does_not_emit_swap_formation_event():
    owner = _unit(
        "e7e66be4",
        {
            "id": "set2.passive.yossarian",
            "name": "Yossarian",
            "effect": "swap_enemy_line",
            "runtime": {"type": "swap_enemy_line"},
        },
        position="back",
    )
    target = _unit("opp_1")
    events = []

    PassiveProcessor().before_attack(
        owner,
        target,
        [owner],
        [target],
        lambda event_type, payload: events.append((event_type, payload)),
        "team_a",
        3.75,
    )

    assert not [payload for event_type, payload in events if event_type == "formation_changed"]
    assert target.position == "front"


def test_scheduled_bonus_attack_delivers_formation_before_bonus_hit_and_replays():
    owner = _unit(
        "e7e66be4",
        {
            "id": "set2.passive.yossarian",
            "name": "Yossarian",
            "effect": "swap_enemy_line",
            "runtime": {"type": "swap_enemy_line"},
        },
        position="back",
        attack_speed=1.0,
        mana_on_attack=100,
    )
    target = _unit("opp_1", hp=5000, attack_speed=0.0)
    events = []

    CombatSimulator(dt=0.1, timeout=2.0).simulate(
        [owner],
        [target],
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
    )

    formation_index = next(index for index, (event_type, _) in enumerate(events) if event_type == "formation_changed")
    bonus_attack_index = next(
        index for index, (event_type, payload) in enumerate(events)
        if event_type == "unit_attack" and payload.get("bonus_attack")
    )
    assert formation_index < bonus_attack_index
    formation = events[formation_index][1]
    assert formation["previous_position"] == "front"
    assert formation["new_position"] == "back"
    assert isinstance(formation["seq"], int)
    assert formation["event_id"]
    assert formation["seq"] < events[bonus_attack_index][1]["seq"]

    assert target.position == "back"
