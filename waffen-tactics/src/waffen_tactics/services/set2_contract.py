"""Fail-closed structural checks for the author-led Set 2 data contract.

This module contains only the locked structural invariants and explicit
removals from the author contract.  It does not contain balance values, trait
effects, or runtime dispatch.  It validates data supplied by the author before
a future dataset is allowed to become a canonical runtime source.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any


SET2_ROSTER_SIZE = 32
SET2_COST_DISTRIBUTION = {1: 6, 2: 7, 3: 8, 4: 6, 5: 5}
SET2_TRAIT_COUNT = 12
SET2_REMOVED_TRAIT_NAMES = frozenset({"Żołnierz mentora"})


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


def _numeric_tier_signature(tier: Any) -> tuple[Any, ...] | None:
    """Return authored numeric values for a tier when its shape exposes them."""

    if not isinstance(tier, Sequence) or isinstance(tier, (str, bytes)):
        return None

    values: list[Any] = []
    for effect in tier:
        if not _is_object(effect):
            return None
        authored_effect = effect.get("effect")
        if _is_object(authored_effect) and isinstance(authored_effect.get("value"), (int, float)) and not isinstance(authored_effect.get("value"), bool):
            values.append(authored_effect["value"])
            continue
        rewards = effect.get("rewards")
        if not isinstance(rewards, Sequence) or isinstance(rewards, (str, bytes)):
            return None
        reward_values = [
            reward.get("value")
            for reward in rewards
            if _is_object(reward) and isinstance(reward.get("value"), (int, float)) and not isinstance(reward.get("value"), bool)
        ]
        if not reward_values:
            return None
        values.append(reward_values[0])
    return tuple(values) if values else None


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
        else:
            removed_traits = sorted(set(traits).intersection(SET2_REMOVED_TRAIT_NAMES))
            errors.extend(
                f"{path}.traits contains removed Set 2 trait: {trait_name}"
                for trait_name in removed_traits
            )
            if len(traits) != 2 and not _non_empty_string(record.get("trait_exception")):
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
    expected_count: int | None = SET2_TRAIT_COUNT,
) -> list[str]:
    """Return deterministic validation errors for tiered Set 2 trait data.

    The accepted Set 2 contract contains 12 traits.  ``expected_count`` stays
    overridable so callers can validate an explicitly scoped fixture without
    weakening the default contract.
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
        elif trait["name"] in SET2_REMOVED_TRAIT_NAMES:
            errors.append(f"{path}.name is a removed Set 2 trait: {trait['name']}")

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

        # Multi-tier records with a numeric authored value must not silently
        # repeat an adjacent tier value. Two-tier contracts are intentionally
        # allowed here because some binary traits are not percentage-scaled.
        if len(tiers) > 2:
            signatures = [_numeric_tier_signature(tier) for tier in tiers]
            if all(signature is not None for signature in signatures):
                repeated = any(left == right for left, right in zip(signatures, signatures[1:]))
                if repeated:
                    errors.append(f"{path}.modular_effects contains repeated adjacent numeric tier values")

    duplicates = sorted({trait_id for trait_id in ids if ids.count(trait_id) > 1})
    errors.extend(f"duplicate trait id: {trait_id}" for trait_id in duplicates)
    return errors
