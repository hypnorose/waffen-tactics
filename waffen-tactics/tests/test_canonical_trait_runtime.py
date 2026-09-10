"""Regression coverage for canonical modular trait effects in combat runtime."""

import copy
import json
from pathlib import Path

from waffen_tactics.models.unit import Skill, Stats, Unit
from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit
from waffen_tactics.services.synergy import SynergyEngine


TRAITS_PATH = Path(__file__).parents[1] / "traits.json"


def _load_traits():
    with TRAITS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)["traits"]


def _unit(unit_id, name, factions=(), classes=()):
    return Unit(
        id=unit_id,
        name=name,
        cost=1,
        factions=list(factions),
        classes=list(classes),
        stats=Stats(attack=50, hp=500, defense=20, max_mana=100, attack_speed=1.0),
        skill=Skill(name="test", description="test"),
    )


def _combat_unit(unit_id, name, effects=None, hp=100, attack=20, defense=5, attack_speed=1.0, position="front"):
    stats = Stats(
        attack=attack,
        hp=hp,
        defense=defense,
        max_mana=100,
        attack_speed=attack_speed,
        mana_on_attack=0,
        mana_regen=0,
    )
    return CombatUnit(
        id=unit_id,
        name=name,
        hp=hp,
        attack=attack,
        defense=defense,
        attack_speed=attack_speed,
        effects=copy.deepcopy(effects or []),
        max_mana=100,
        stats=stats,
        position=position,
    )


def test_canonical_death_effects_are_attached_with_target_and_tier_semantics():
    engine = SynergyEngine(_load_traits())

    streamer = _unit("streamer-1", "Streamer", factions=["Streamer"])
    non_streamer = _unit("other-1", "Other")
    active = {"Streamer": (2, 1)}

    streamer_effects = engine.get_active_effects(streamer, active)
    team_effects = engine.get_active_effects(non_streamer, active)

    assert len(streamer_effects) == 1
    assert streamer_effects[0]["trigger"] == "on_enemy_death"
    assert streamer_effects[0]["rewards"] == [
        {"type": "stat_buff", "stat": "attack", "value": 3},
        {"type": "stat_buff", "stat": "defense", "value": 3},
    ]
    assert team_effects == streamer_effects

    # The death reward is not a start-of-combat stat bonus.
    assert engine.apply_stat_buffs(
        {"hp": 500, "attack": 50, "defense": 20, "attack_speed": 1.0},
        streamer,
        active,
    ) == {"hp": 500, "attack": 50, "defense": 20, "attack_speed": 1.0}


def test_canonical_tiered_death_effects_cover_known_target_contracts():
    engine = SynergyEngine(_load_traits())

    # Team-targeted canonical effects.
    for trait_name, reward_type in (
        ("Denciak", "resource"),
        ("XN Waffen", "stat_buff"),
        ("XN KGB", "stat_buff"),
    ):
        trait_unit = _unit(f"{trait_name}-1", trait_name, factions=[trait_name])
        effects = engine.get_active_effects(trait_unit, {trait_name: (3, 1)})
        assert effects, trait_name
        assert effects[0]["trigger"] in {"on_enemy_death", "on_ally_death"}
        assert effects[0]["rewards"][0]["type"] == reward_type

    # Self-targeted canonical effect must not leak to a non-trait unit.
    hitman = _unit("hitman-1", "Hitman", factions=["Hitman"])
    other = _unit("other-2", "Other")
    active = {"Hitman": (1, 1)}
    assert engine.get_active_effects(hitman, active)
    assert engine.get_active_effects(other, active) == []


def test_canonical_streamer_death_reward_applies_after_death_once_via_events():
    engine = SynergyEngine(_load_traits())
    trait_unit = _unit("streamer-1", "Streamer", factions=["Streamer"])
    effect = engine.get_active_effects(trait_unit, {"Streamer": (2, 1)})[0]

    attacker = _combat_unit("a1", "Streamer", effects=[effect], hp=100, attack=100, defense=10)
    victim = _combat_unit("b1", "Victim", hp=10, attack=1, defense=1, attack_speed=0.5)
    events = []

    CombatSimulator(dt=0.1, timeout=5).simulate(
        [attacker],
        [victim],
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
    )

    death_index = next(i for i, (event_type, _) in enumerate(events) if event_type == "unit_died")
    buff_events = [payload for event_type, payload in events if event_type == "stat_buff"]
    assert [payload["stat"] for payload in buff_events] == ["attack", "defense"]
    assert all(i > death_index for i, (event_type, _) in enumerate(events) if event_type == "stat_buff")
    assert attacker.attack == 103
    assert attacker.defense == 13


def test_death_trigger_does_not_fire_for_the_wrong_team():
    wrong_side_effect = [{
        "trigger": "on_ally_death",
        "conditions": {"chance_percent": 100},
        "rewards": [{"type": "resource", "resource": "gold", "value": 7}],
    }]
    attacker = _combat_unit("a1", "WrongSide", effects=wrong_side_effect, hp=100, attack=100, defense=10)
    victim = _combat_unit("b1", "Victim", hp=10, attack=1, defense=1, attack_speed=0.5)
    survivor = _combat_unit("b2", "AllyReactor", effects=wrong_side_effect, hp=100, attack=1, defense=1, attack_speed=0.5)
    events = []

    CombatSimulator(dt=0.1, timeout=5).simulate(
        [attacker],
        [victim, survivor],
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
    )

    gold_events = [payload for event_type, payload in events if event_type == "gold_reward"]
    assert len(gold_events) == 1
    assert gold_events[0]["unit_id"] == "b2"


def test_canonical_per_second_effect_runs_in_shared_simulator_lifecycle():
    engine = SynergyEngine(_load_traits())
    trait_unit = _unit("guard-1", "Srebrna Gwardia", factions=["Srebrna Gwardia"])
    effect = engine.get_active_effects(trait_unit, {"Srebrna Gwardia": (1, 1)})[0]
    unit = _combat_unit("a1", "Guard", effects=[effect], hp=100, attack=1, defense=10)
    enemy = _combat_unit("b1", "Enemy", hp=1000, attack=1, defense=1)
    events = []

    CombatSimulator(dt=0.1, timeout=0.05).simulate(
        [unit],
        [enemy],
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
    )

    stat_events = [payload for event_type, payload in events if event_type == "stat_buff"]
    assert len(stat_events) == 1
    assert stat_events[0]["stat"] == "defense"
    assert stat_events[0]["amount"] == 3
    assert stat_events[0]["cause"] == "per_second_trait"
    assert unit.defense == 13


def test_canonical_per_round_effect_uses_round_scaled_hp_and_mirror():
    engine = SynergyEngine(_load_traits())
    trait_unit = _unit("old-1", "Starokurwy", factions=["Starokurwy"])
    effect = engine.get_active_effects(trait_unit, {"Starokurwy": (1, 1)})[0]
    unit = _combat_unit("a1", "Old", effects=[effect], hp=100, attack=1, defense=1)
    unit.max_hp = 500
    enemy = _combat_unit("b1", "Enemy", hp=1000, attack=1, defense=1)
    events = []

    CombatSimulator(dt=0.1, timeout=0.05).simulate(
        [unit],
        [enemy],
        round_number=2,
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
    )

    heals = [payload for event_type, payload in events if event_type == "heal"]
    assert len(heals) == 1
    assert heals[0]["amount"] == 30
    assert heals[0]["pre_hp"] == 100
    assert heals[0]["post_hp"] == 130
    assert unit.hp == 130


def test_canonical_ally_threshold_heals_damaged_ally_once_at_crossing():
    engine = SynergyEngine(_load_traits())
    trait_unit = _unit("exile-1", "Wygnaniec", factions=["Wygnaniec"])
    effect = engine.get_active_effects(trait_unit, {"Wygnaniec": (1, 1)})[0]
    owner = _combat_unit("a1", "Exile", effects=[effect], hp=500, attack=1, defense=1, position="back")
    ally = _combat_unit("a2", "Ally", hp=200, attack=1, defense=1, position="front")
    ally.max_hp = 500
    enemy = _combat_unit("b1", "Attacker", hp=1000, attack=100, defense=1, attack_speed=1.0)
    events = []

    CombatSimulator(dt=0.1, timeout=1.5).simulate(
        [owner, ally],
        [enemy],
        event_callback=lambda event_type, payload: events.append((event_type, payload)),
    )

    heals = [payload for event_type, payload in events if event_type == "heal" and payload["unit_id"] == "a2"]
    assert len(heals) == 1
    assert heals[0]["amount"] == 250
    assert ally.hp == 351
