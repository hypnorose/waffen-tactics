"""Seeded execution checks for the approved WFT-139 item runtime."""

from __future__ import annotations

import copy

from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.items import ITEMS
from waffen_tactics.services.passive_processor import PassiveProcessor


def item_effect(item_id: str, unit_id: str = "a") -> dict:
    definition = ITEMS[item_id]
    return {
        "type": "item",
        "id": f"item:{unit_id}:0:{item_id}",
        "item_id": item_id,
        "item_effect_id": f"{item_id}:effect",
        "stats": copy.deepcopy(definition["stats"]),
        "effect": copy.deepcopy(definition.get("effect")),
        "description": definition.get("description", ""),
        "slot": 0,
    }


def unit(unit_id: str, hp: int = 1000, attack: int = 10, defense: int = 5, speed: float = 2.0, *, item: str | None = None, max_mana: int = 100) -> CombatUnit:
    effects = [item_effect(item, unit_id)] if item else []
    return CombatUnit(unit_id, unit_id, hp, attack, defense, speed, effects=effects, max_mana=max_mana)


def simulate(player: CombatUnit, opponent: CombatUnit, timeout: float = 3.2):
    events: list[tuple[str, dict]] = []
    result = CombatSimulator(dt=0.1, timeout=timeout).simulate(
        [player], [opponent], lambda event_type, payload: events.append((event_type, payload))
    )
    return result, events


def test_start_shield_is_canonical_and_identified_by_item():
    player = unit("a", hp=1000, item="plaszcz_ze_100_bawelny")
    opponent = unit("b", hp=5000, attack=1, speed=0.1)

    _result, events = simulate(player, opponent, timeout=0.5)

    shield = [payload for event, payload in events if event == "shield_applied"]
    assert shield and shield[0]["amount"] == 300
    assert shield[0]["item_id"] == "plaszcz_ze_100_bawelny"
    assert shield[0]["item_effect_id"] == "plaszcz_ze_100_bawelny:effect"


def test_attack_stack_is_capped_and_preserves_float_attack_speed():
    player = unit("a", item="zestaw_do_makijazu_po_edycie")
    opponent = unit("b")
    processor = PassiveProcessor()
    events: list[tuple[str, dict]] = []

    for timestamp in range(12):
        processor.before_attack(player, opponent, [player], [opponent], lambda t, p: events.append((t, p)), "team_a", float(timestamp))

    assert player.item_runtime_state["zestaw_do_makijazu_po_edycie:0"]["stacks"] == 10
    assert player.attack == 20
    assert player.defense == 15
    assert abs(player.attack_speed - 3.0) < 1e-9
    stack_events = [payload for event, payload in events if event == "stat_buff" and payload.get("item_id")]
    assert stack_events[-1]["stack"] == 10
    assert stack_events[-1]["stack_cap"] == 10


def test_threshold_effect_is_once_per_fight_and_expires():
    player = unit("a", hp=1000, item="kolekcja_syropow")
    processor = PassiveProcessor()
    events: list[tuple[str, dict]] = []
    callback = lambda event_type, payload: events.append((event_type, payload))

    processor.after_damage(player, 1000, 500, [player], [], callback, "team_a", 1.0)
    processor.after_damage(player, 500, 400, [player], [], callback, "team_a", 1.5)

    assert len([payload for event, payload in events if event == "effect_applied" and payload.get("item_id")]) == 1
    assert len([payload for event, payload in events if event == "shield_applied" and payload.get("item_id")]) == 1
    assert player.item_runtime_state["kolekcja_syropow:0"]["threshold_used"] is True
    assert len([effect for effect in player.effects if effect.get("type") == "mana_regen"]) == 1


def test_bonus_attack_and_reflect_are_separate_non_recursive_hits():
    player = unit("a", hp=1000, attack=40, item="fartuszek_femboya", max_mana=10)
    opponent = unit("b", hp=5000, defense=5, item="skruszony_zab", max_mana=100)

    _result, events = simulate(player, opponent, timeout=2.0)

    attacks = [payload for event, payload in events if event == "unit_attack"]
    bonus = [payload for payload in attacks if payload.get("bonus_attack")]
    reflected = [payload for payload in attacks if payload.get("cause") == "item_reflect"]
    assert bonus
    assert bonus[0]["item_id"] == "fartuszek_femboya"
    assert reflected
    assert all(payload["item_id"] == "skruszony_zab" for payload in reflected)
    assert len(reflected) <= len(attacks)


def test_periodic_item_outputs_use_canonical_heal_or_dot_events():
    player = unit("a", hp=1000, item="bluza_z_bytom")
    ally = unit("ally", hp=500, attack=1, speed=0.1)
    ally.max_hp = 1000
    opponent = unit("b", hp=5000, attack=1, speed=0.1)
    events: list[tuple[str, dict]] = []
    simulator = CombatSimulator(dt=0.1, timeout=3.2)
    simulator.simulate([player, ally], [opponent], lambda event_type, payload: events.append((event_type, payload)))

    heals = [payload for event, payload in events if event == "heal" and payload.get("item_id") == "bluza_z_bytom"]
    assert heals
    assert heals[0]["unit_id"] == "ally"
    assert heals[0]["post_hp"] > heals[0]["pre_hp"]


def test_periodic_item_targeting_uses_absolute_hp_and_front_row_scope():
    owner = unit("owner", item="bluza_z_bytom")
    lower_ratio = unit("ratio-low", hp=400)
    lower_ratio.max_hp = 2000
    lower_absolute = unit("absolute-low", hp=300)
    lower_absolute.max_hp = 500
    forteca_owner = unit("forteca-owner", attack=1, item="forteca_z_ksiazek")
    backline = unit("backline", hp=100, speed=0.1)
    backline.position = "back"
    front_enemy = unit("enemy", hp=10000, attack=1, speed=0.1)
    front_enemy.position = "front"

    events: list[tuple[str, dict]] = []
    simulator = CombatSimulator(dt=0.1, timeout=3.2)
    simulator.simulate(
        [owner, lower_ratio, lower_absolute, forteca_owner],
        [front_enemy, backline],
        lambda event_type, payload: events.append((event_type, payload)),
    )

    heals = [payload for event, payload in events if event == "heal" and payload.get("item_id") == "bluza_z_bytom"]
    assert heals and heals[0]["unit_id"] == "absolute-low"
    ticks = [payload for event, payload in events if event == "damage_over_time_tick" and payload.get("item_id") == "forteca_z_ksiazek"]
    assert ticks and all(payload["unit_id"] == "enemy" for payload in ticks)


def test_shared_regen_replaces_one_dead_assignment_without_accumulating():
    owner = unit("owner", item="encyklopedia_seksu")
    allies = [unit(f"ally-{index}") for index in range(1, 4)]
    processor = PassiveProcessor()
    events: list[tuple[str, dict]] = []
    callback = lambda event_type, payload: events.append((event_type, payload))

    processor.initialize([owner, *allies], [], callback, timestamp=0.0)
    state = owner.item_runtime_state["encyklopedia_seksu:0"]
    assigned_ids = set(state["assigned_targets"])
    dead = next(ally for ally in allies if ally.id in assigned_ids)
    surviving = [ally for ally in [owner, *allies] if ally is not dead]

    processor.on_unit_death(dead, surviving, [], callback, "team_a", 2.0)
    processor.on_unit_death(dead, surviving, [], callback, "team_a", 3.0)

    replacements = [
        payload for event, payload in events
        if event == "regen_gain" and payload.get("target") == "replacement_ally"
    ]
    assert len(replacements) == 1
    assert replacements[0]["amount_per_sec"] == 12
    assert state["assigned_targets"].count(replacements[0]["unit_id"]) == 1


def test_item_runtime_state_resets_between_fights():
    player = unit("a", item="zestaw_do_makijazu_po_edycie")
    opponent = unit("b", hp=5000)
    simulator = CombatSimulator(dt=0.1, timeout=0.6)

    simulator.simulate([player], [opponent], lambda _event_type, _payload: None)
    first_state = copy.deepcopy(player.item_runtime_state)
    simulator.simulate([player], [opponent], lambda _event_type, _payload: None)

    assert first_state["zestaw_do_makijazu_po_edycie:0"]["stacks"] == 1
    assert player.item_runtime_state["zestaw_do_makijazu_po_edycie:0"]["stacks"] == 1
