"""Deterministic coverage matrix for the currently loaded canonical passives and traits.

The matrix intentionally exercises the shared-core data and runtime contracts.
It does not invent authored content or duplicate combat rules in a test helper.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import random
from pathlib import Path

import pytest

from waffen_tactics.models.unit import Skill, Stats, Unit
from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.event_canonicalizer import emit_damage
from waffen_tactics.services.passive_definitions import (
    PASSIVE_DEFINITIONS,
    get_passive_definition,
)
from waffen_tactics.services.passive_processor import PassiveProcessor
from waffen_tactics.services.synergy import SynergyEngine


ROOT = Path(__file__).resolve().parents[1]
TRAITS_PATH = ROOT / "traits.json"


def _load_traits() -> list[dict]:
    with TRAITS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)["traits"]


def _unit_with_trait(trait_name: str, unit_id: str, trait_type: str) -> Unit:
    stats = Stats(
        attack=10,
        hp=100,
        defense=5,
        max_mana=100,
        attack_speed=1.0,
        mana_on_attack=10,
        mana_regen=0,
    )
    return Unit(
        id=unit_id,
        name=unit_id,
        cost=1,
        factions=[trait_name] if trait_type == "faction" else [],
        classes=[trait_name] if trait_type != "faction" else [],
        stats=stats,
        skill=Skill(name="matrix", description="matrix"),
    )


def _trait_state(trait: dict, count: int, seed: int) -> dict:
    units = [
        _unit_with_trait(trait["name"], f"{trait['name']}-{index}", trait.get("type", "class"))
        for index in range(count)
    ]
    random.Random(seed).shuffle(units)
    return SynergyEngine(_load_traits()).compute(units)


TRAIT_ROWS = tuple(
    (trait, tier, threshold, thresholds[tier + 1] if tier + 1 < len(thresholds) else None)
    for trait in _load_traits()
    for thresholds in [trait.get("thresholds", [])]
    for tier, threshold in enumerate(thresholds)
)


# One canonical representative per runtime trigger family.  Keeping this
# registry explicit makes a newly introduced family fail the matrix until it
# receives both a positive and a boundary/negative scenario below.
PASSIVE_FAMILY_REPRESENTATIVES = {
    "ally_threshold": "grzalcia",
    "attack_count": "falconbalkon",
    "attack_count_same_target": "puszmen12",
    "bonus_attack": "capybara",
    "conditional_attack": "laylo",
    "kill": "stalin",
    "position_scope_start": "szalwia",
    "position_start": "kubica",
    "start_effect": "mrvlook",
    "start_enemy_debuff": "galanonim",
    "start_enemy_highest_attack": "szachowymentor",
    "start_scope_stat": "dawid_czerw",
    "start_stat": "olsak",
    "start_target": "miki",
    "start_target_bonus": "operatorkosiarki",
    "threshold": "rafcikd",
}


def _passive_unit(passive_id: str, *, hp: int = 1000, position: str = "front") -> CombatUnit:
    stats = Stats(
        attack=20,
        hp=hp,
        defense=5,
        max_mana=100,
        attack_speed=1.0,
        mana_on_attack=10,
        mana_regen=0,
    )
    return CombatUnit(
        id=f"family-{passive_id}",
        name=passive_id,
        hp=hp,
        attack=20,
        defense=5,
        attack_speed=1.0,
        max_mana=100,
        stats=stats,
        position=position,
        passive=copy.deepcopy(get_passive_definition(passive_id)),
    )


def _stable_event_signature(events: list[tuple[str, dict]]) -> tuple:
    def stable_payload(value):
        if isinstance(value, dict):
            return {
                key: stable_payload(child)
                for key, child in value.items()
                if key not in {"event_id", "effect_id", "id"}
            }
        if isinstance(value, list):
            return [stable_payload(child) for child in value]
        return value

    return tuple(
        (
            event_type,
            json.dumps(stable_payload(payload), ensure_ascii=False, sort_keys=True, default=str),
        )
        for event_type, payload in events
    )


def _family_events(passive_id: str, positive: bool) -> list[tuple[str, dict]]:
    family = PASSIVE_DEFINITIONS[passive_id]["kind"]
    events: list[tuple[str, dict]] = []
    callback = lambda event_type, payload: events.append((event_type, payload))
    processor = PassiveProcessor()
    owner = _passive_unit(passive_id)
    target = _passive_unit("family-target", hp=1000)

    if family in {
        "position_scope_start",
        "position_start",
        "start_effect",
        "start_enemy_debuff",
        "start_enemy_highest_attack",
        "start_scope_stat",
        "start_stat",
        "start_target",
        "start_target_bonus",
    }:
        processor.initialize([owner], [target], callback, timestamp=0.0)
        if not positive:
            # A second lifecycle entry must not retrigger a start passive.
            processor.initialize([owner], [target], callback, timestamp=1.0)
        return events

    if family == "attack_count":
        every = int(owner.passive["every"])
        for _ in range(every if positive else every - 1):
            processor.before_attack(owner, target, [owner], [target], callback, "team_a", 0.0)
        return events

    if family == "attack_count_same_target":
        every = int(owner.passive["every"])
        for _ in range(every + 1 if positive else every):
            processor.before_attack(owner, target, [owner], [target], callback, "team_a", 0.0)
        return events

    if family == "bonus_attack":
        if positive:
            processor.bonus_attack_plan(owner, target, [owner], [target], callback, "team_a", 0.0)
        else:
            processor.before_attack(owner, target, [owner], [target], callback, "team_a", 0.0)
        return events

    if family == "threshold":
        threshold = float(owner.passive["threshold"])
        old_hp = int(owner.max_hp * (threshold + 2) / 100)
        new_hp = int(owner.max_hp * (threshold - 1 if positive else threshold + 1) / 100)
        processor.after_damage(owner, old_hp, new_hp, [owner], [target], callback, "team_a", 0.0)
        return events

    if family == "ally_threshold":
        ally = _passive_unit("family-ally")
        threshold = float(owner.passive["threshold"])
        old_hp = int(ally.max_hp * (threshold + 2) / 100)
        new_hp = int(ally.max_hp * (threshold - 1 if positive else threshold + 1) / 100)
        processor.after_damage(ally, old_hp, new_hp, [owner, ally], [target], callback, "team_a", 0.0)
        return events

    if family == "conditional_attack":
        threshold = float(owner.passive["threshold"])
        desired_hp = int(target.max_hp * (threshold - 1 if positive else threshold + 1) / 100)
        emit_damage(None, None, target, raw_damage=target.hp - desired_hp, emit_event=False)
        plan = processor.before_attack(owner, target, [owner], [target], callback, "team_a", 0.0)
        if positive:
            assert plan.get("damage_multiplier", 1) > 1
        else:
            assert "damage_multiplier" not in plan
        return events

    if family == "kill":
        if positive:
            processor.on_kill(owner, [owner], [target], callback, "team_a", 0.0)
        else:
            # Use another canonical definition to verify the kill dispatcher
            # does not infer a kill effect from unrelated passive data.
            non_kill = _passive_unit("maxas12")
            processor.on_kill(non_kill, [non_kill], [target], callback, "team_a", 0.0)
        return events

    raise AssertionError(f"Unhandled canonical passive family: {family}")


@pytest.mark.parametrize(
    "family,passive_id",
    tuple(sorted(PASSIVE_FAMILY_REPRESENTATIVES.items())),
    ids=lambda value: value if isinstance(value, str) else str(value),
)
def test_passive_trigger_family_matrix_has_positive_and_negative_path(family: str, passive_id: str):
    definition = get_passive_definition(passive_id)
    assert definition is not None
    assert definition["kind"] == family

    positive_events = _family_events(passive_id, positive=True)
    negative_events = _family_events(passive_id, positive=False)

    if family in {
        "position_scope_start",
        "position_start",
        "start_effect",
        "start_enemy_debuff",
        "start_enemy_highest_attack",
        "start_scope_stat",
        "start_stat",
        "start_target",
        "start_target_bonus",
    }:
        assert _stable_event_signature(positive_events) == _stable_event_signature(negative_events)
        assert sum(
            event_type == "passive_triggered" and payload.get("effect") == "passive_ready"
            for event_type, payload in positive_events
        ) == 1
    elif family in {"threshold", "ally_threshold", "attack_count", "attack_count_same_target"}:
        assert any(event_type == "passive_triggered" for event_type, _ in positive_events)
        assert not any(event_type == "passive_triggered" for event_type, _ in negative_events)
    elif family == "bonus_attack":
        assert any(payload.get("trigger") == "on_bonus_attack" for event_type, payload in positive_events if event_type == "passive_triggered")
        assert not any(event_type == "passive_triggered" for event_type, _ in negative_events)
    elif family == "conditional_attack":
        assert any(event_type == "passive_triggered" for event_type, _ in positive_events)
        assert not negative_events
    elif family == "kill":
        assert any(payload.get("trigger") == "on_kill" for event_type, payload in positive_events if event_type == "passive_triggered")
        assert not negative_events


@pytest.mark.parametrize(
    "trait,tier,threshold,next_threshold",
    TRAIT_ROWS,
    ids=lambda value: value["name"] if isinstance(value, dict) else str(value),
)
def test_trait_threshold_matrix_covers_below_exact_and_next_boundary(
    trait: dict,
    tier: int,
    threshold: int,
    next_threshold: int | None,
):
    """Every canonical tier has deterministic negative and positive boundaries."""

    trait_name = trait["name"]
    tier_number = tier + 1
    below = _trait_state(trait, max(0, threshold - 1), 520000 + tier)
    exact = _trait_state(trait, threshold, 520000 + tier)

    if tier == 0:
        assert trait_name not in below
    else:
        assert below[trait_name] == (threshold - 1, tier_number - 1)
    assert exact[trait_name] == (threshold, tier_number)

    if next_threshold is not None:
        next_state = _trait_state(trait, next_threshold, 520000 + tier)
        assert next_state[trait_name] == (next_threshold, tier_number + 1)


def _passive_combat_signature(passive_id: str, seed: int) -> tuple:
    passive = copy.deepcopy(get_passive_definition(passive_id))
    assert passive is not None

    unit_stats = Stats(
        attack=20,
        hp=1000,
        defense=5,
        max_mana=100,
        attack_speed=1.0,
        mana_on_attack=10,
        mana_regen=0,
    )
    unit = CombatUnit(
        id=f"matrix-{passive_id}",
        name=passive_id,
        hp=1000,
        attack=20,
        defense=5,
        attack_speed=1.0,
        max_mana=100,
        stats=unit_stats,
        position="front",
        passive=passive,
    )
    target_stats = Stats(
        attack=1,
        hp=100000,
        defense=1,
        max_mana=100,
        attack_speed=0.0,
        mana_on_attack=0,
        mana_regen=0,
    )
    target = CombatUnit(
        id="matrix-target",
        name="matrix-target",
        hp=100000,
        attack=1,
        defense=1,
        attack_speed=0.0,
        max_mana=100,
        stats=target_stats,
        position="front",
    )
    events: list[tuple[str, dict]] = []
    random.seed(seed)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        result = CombatSimulator(dt=0.1, timeout=0.2).simulate(
            [unit],
            [target],
            event_callback=lambda event_type, payload: events.append((event_type, payload)),
        )

    def stable_payload(value):
        if isinstance(value, dict):
            return {
                key: stable_payload(child)
                for key, child in value.items()
                if key not in {"event_id", "effect_id", "id"}
            }
        if isinstance(value, list):
            return [stable_payload(child) for child in value]
        return value

    event_signature = tuple(
        (
            event_type,
            json.dumps(stable_payload(payload), ensure_ascii=False, sort_keys=True, default=str),
        )
        for event_type, payload in events
    )
    result_signature = tuple(
        (key, result.get(key))
        for key in ("winner", "duration", "timeout", "team_a_survivors", "team_b_survivors")
    )
    return result_signature, event_signature


@pytest.mark.parametrize("passive_id", tuple(PASSIVE_DEFINITIONS), ids=str)
def test_passive_matrix_replays_every_canonical_definition_deterministically(passive_id: str):
    first = _passive_combat_signature(passive_id, 530000 + tuple(PASSIVE_DEFINITIONS).index(passive_id))
    second = _passive_combat_signature(passive_id, 530000 + tuple(PASSIVE_DEFINITIONS).index(passive_id))
    definition = get_passive_definition(passive_id)

    assert definition is not None
    assert definition.get("kind")
    assert definition.get("description")
    assert first == second


def test_passive_matrix_rejects_unknown_definition_without_fallback():
    assert get_passive_definition("matrix-unknown-passive") is None
