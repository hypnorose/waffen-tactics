"""Synthetic contract tests; these records are not approved Set 2 content."""

from __future__ import annotations

from copy import deepcopy

from waffen_tactics.services.set2_contract import (
    validate_set2_roster,
    validate_set2_traits,
)


def _passive():
    return {
        "trigger": "on_bonus_attack",
        "condition": {},
        "target": "self",
        "effect": {"kind": "synthetic_effect"},
        "limit": {"activations": 1},
    }


def _roster():
    costs = [1] * 6 + [2] * 7 + [3] * 8 + [4] * 6 + [5] * 5
    return [
        {
            "id": f"synthetic-unit-{index}",
            "name": f"Synthetic Unit {index}",
            "cost": cost,
            "role": "fighter",
            "traits": ["synthetic_trait_a", "synthetic_trait_b"],
            "passive": _passive(),
        }
        for index, cost in enumerate(costs)
    ]


def _traits(count=13):
    return [
        {
            "id": f"synthetic-trait-{index}",
            "name": f"Synthetic Trait {index}",
            "thresholds": [2, 4],
            "modular_effects": [[_passive()], [_passive()]],
        }
        for index in range(count)
    ]


def test_synthetic_set2_roster_contract_accepts_baseline_shape_and_costs():
    assert validate_set2_roster(_roster()) == []


def test_set2_roster_contract_rejects_cost_distribution_and_missing_trait_exception():
    roster = _roster()
    roster[0]["cost"] = 2
    roster[1]["traits"] = ["synthetic_trait_a"]

    errors = validate_set2_roster(roster)

    assert any("cost distribution mismatch" in error for error in errors)
    assert any("trait_exception" in error for error in errors)


def test_set2_roster_contract_rejects_duplicate_ids_and_incomplete_modular_passive():
    roster = _roster()
    roster[1]["id"] = roster[0]["id"]
    del roster[2]["passive"]["limit"]

    errors = validate_set2_roster(roster)

    assert "duplicate unit id: synthetic-unit-0" in errors
    assert "unit[2].passive missing required field 'limit'" in errors


def test_set2_roster_contract_rejects_removed_trait_membership():
    roster = _roster()
    roster[0]["traits"][0] = "Żołnierz mentora"

    errors = validate_set2_roster(roster)

    assert "unit[0].traits contains removed Set 2 trait: Żołnierz mentora" in errors


def test_set2_traits_contract_accepts_explicit_author_count_when_provided():
    assert validate_set2_traits(_traits(), expected_count=13) == []


def test_set2_traits_contract_defaults_to_accepted_twelve_trait_scope():
    errors = validate_set2_traits(_traits())

    assert "traits must contain exactly 12 records, got 13" in errors


def test_set2_traits_contract_rejects_removed_trait_record():
    traits = _traits(12)
    traits[0]["name"] = "Żołnierz mentora"

    errors = validate_set2_traits(traits)

    assert "trait[0].name is a removed Set 2 trait: Żołnierz mentora" in errors


def test_set2_traits_contract_rejects_unsorted_thresholds_and_missing_effect_contract():
    traits = deepcopy(_traits(1))
    traits[0]["thresholds"] = [4, 2]
    del traits[0]["modular_effects"][0][0]["target"]

    errors = validate_set2_traits(traits, expected_count=1)

    assert any("thresholds must be a sorted list" in error for error in errors)
    assert "trait[0].modular_effects[0][0] missing required field 'target'" in errors


def test_set2_traits_contract_rejects_malformed_threshold_type_without_raising():
    traits = deepcopy(_traits(1))
    traits[0]["thresholds"] = {"not": "a list"}

    errors = validate_set2_traits(traits, expected_count=1)

    assert any("thresholds must be a sorted list" in error for error in errors)
    assert any("modular_effects must match" in error for error in errors)


def test_set2_traits_contract_rejects_repeated_adjacent_numeric_tier_values():
    traits = _traits(1)
    traits[0]["thresholds"] = [2, 4, 6]
    tiers = []
    for value in (10, 10, 20):
        effect = _passive()
        effect["effect"]["value"] = value
        tiers.append([effect])
    traits[0]["modular_effects"] = tiers

    errors = validate_set2_traits(traits, expected_count=1)

    assert "trait[0].modular_effects contains repeated adjacent numeric tier values" in errors
