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
from waffen_tactics.services.passive_definitions import (
    PASSIVE_DEFINITIONS,
    get_passive_definition,
)
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
