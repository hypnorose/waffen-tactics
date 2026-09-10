"""Fail-closed structural checks for the author-led Set 2 data contract.

This module deliberately contains no Set 2 names, numbers, trait effects, or
runtime dispatch.  It validates data supplied by the author before a future
dataset is allowed to become a canonical runtime source.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any


SET2_ROSTER_SIZE = 32
SET2_COST_DISTRIBUTION = {1: 6, 2: 7, 3: 8, 4: 6, 5: 5}


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_object(value: Any) -> bool:
    return isinstance(value, Mapping)


def _validate_modular_effect(effect: Any, path: str) -> list[str]:
    """Validate one atomic ``trigger -> condition -> target -> effect -> limit`` node."""

    if not _is_object(effect):
        return [f"{path} must be an object"]

    errors: list[str] = []
    for field in ("trigger", "target"):
        if field not in effect:
            errors.append(f"{path} missing required field '{field}'")
        elif not _non_empty_string(effect[field]):
            errors.append(f"{path}.{field} must be a non-empty string")

    condition_field = "condition" if "condition" in effect else "conditions"
    if condition_field not in effect:
        errors.append(f"{path} missing required field 'condition' (or 'conditions')")
    elif not _is_object(effect[condition_field]):
        errors.append(f"{path}.{condition_field} must be an object")

    if "effect" not in effect:
        errors.append(f"{path} missing required field 'effect'")
    else:
        effect_value = effect["effect"]
        if isinstance(effect_value, Sequence) and not isinstance(effect_value, (str, bytes)):
            if not effect_value:
                errors.append(f"{path}.effect must not be empty")
            elif not all(_is_object(item) for item in effect_value):
                errors.append(f"{path}.effect list entries must be objects")
        elif not _is_object(effect_value):
            errors.append(f"{path}.effect must be an object or a non-empty list of objects")

    if "limit" not in effect:
        errors.append(f"{path} missing required field 'limit'")
    elif not _is_object(effect["limit"]):
        errors.append(f"{path}.limit must be an object")

    return errors


def validate_set2_roster(
    records: Any,
    *,
    expected_count: int = SET2_ROSTER_SIZE,
    expected_costs: Mapping[int, int] = SET2_COST_DISTRIBUTION,
) -> list[str]:
    """Return deterministic validation errors for a proposed Set 2 roster.

    The validator checks the structural contract only.  It does not decide
    whether an author-provided name, value, role, trait, or passive is good
    design, and it never mutates the supplied records.
    """

    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return ["roster must be a list of unit records"]

    errors: list[str] = []
    if len(records) != expected_count:
        errors.append(f"roster must contain exactly {expected_count} units, got {len(records)}")

    ids: list[str] = []
    costs: list[int] = []

    for index, record in enumerate(records):
        path = f"unit[{index}]"
        if not _is_object(record):
            errors.append(f"{path} must be an object")
            continue

        unit_id = record.get("id")
        if not _non_empty_string(unit_id):
            errors.append(f"{path}.id must be a non-empty string")
        else:
            ids.append(unit_id)

        for field in ("name", "role"):
            if not _non_empty_string(record.get(field)):
                errors.append(f"{path}.{field} must be a non-empty string")

        cost = record.get("cost")
        if not isinstance(cost, int) or isinstance(cost, bool) or cost not in expected_costs:
            errors.append(
                f"{path}.cost must be one of {sorted(expected_costs)}, got {cost!r}"
            )
        else:
            costs.append(cost)

        traits = record.get("traits")
        if not isinstance(traits, list) or not all(_non_empty_string(item) for item in traits):
            errors.append(f"{path}.traits must be a list of non-empty strings")
        elif len(traits) != 2 and not _non_empty_string(record.get("trait_exception")):
            errors.append(
                f"{path} must contain exactly two traits or a non-empty 'trait_exception'"
            )

        passive = record.get("passive")
        errors.extend(_validate_modular_effect(passive, f"{path}.passive"))

    duplicates = sorted({unit_id for unit_id in ids if ids.count(unit_id) > 1})
    errors.extend(f"duplicate unit id: {unit_id}" for unit_id in duplicates)

    actual_costs = Counter(costs)
    expected_costs_counter = Counter(expected_costs)
    if actual_costs != expected_costs_counter:
        errors.append(
            "cost distribution mismatch: "
            f"expected {dict(sorted(expected_costs_counter.items()))}, "
            f"got {dict(sorted(actual_costs.items()))}"
        )

    return errors


def validate_set2_traits(
    traits: Any,
    *,
    expected_count: int | None = None,
) -> list[str]:
    """Return deterministic validation errors for tiered Set 2 trait data.

    ``expected_count`` is intentionally optional while the author decision
    between the 12-trait draft and the 13-trait task scope is unresolved.
    """

    if not isinstance(traits, Sequence) or isinstance(traits, (str, bytes)):
        return ["traits must be a list of trait records"]

    errors: list[str] = []
    if expected_count is not None and len(traits) != expected_count:
        errors.append(f"traits must contain exactly {expected_count} records, got {len(traits)}")

    ids: list[str] = []
    for index, trait in enumerate(traits):
        path = f"trait[{index}]"
        if not _is_object(trait):
            errors.append(f"{path} must be an object")
            continue

        trait_id = trait.get("id")
        if not _non_empty_string(trait_id):
            errors.append(f"{path}.id must be a non-empty string")
        else:
            ids.append(trait_id)

        if not _non_empty_string(trait.get("name")):
            errors.append(f"{path}.name must be a non-empty string")

        thresholds = trait.get("thresholds")
        valid_thresholds = (
            isinstance(thresholds, list)
            and bool(thresholds)
            and all(_is_positive_int(value) for value in thresholds)
            and thresholds == sorted(set(thresholds))
        )
        if not valid_thresholds:
            errors.append(f"{path}.thresholds must be a sorted list of unique positive integers")

        tiers = trait.get("modular_effects")
        threshold_count = len(thresholds) if isinstance(thresholds, list) else None
        if not isinstance(tiers, list) or threshold_count is None or len(tiers) != threshold_count:
            errors.append(f"{path}.modular_effects must match the thresholds length")
            continue

        for tier_index, tier in enumerate(tiers):
            tier_path = f"{path}.modular_effects[{tier_index}]"
            if not isinstance(tier, list) or not tier:
                errors.append(f"{tier_path} must be a non-empty list")
                continue
            for effect_index, effect in enumerate(tier):
                errors.extend(
                    _validate_modular_effect(
                        effect,
                        f"{tier_path}[{effect_index}]",
                    )
                )

    duplicates = sorted({trait_id for trait_id in ids if ids.count(trait_id) > 1})
    errors.extend(f"duplicate trait id: {trait_id}" for trait_id in duplicates)
    return errors
