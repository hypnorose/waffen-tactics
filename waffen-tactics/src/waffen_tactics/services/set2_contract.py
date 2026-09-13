"""Fail-closed checks for the author-led Set 2 data contract.

This module contains the locked structural invariants and player-facing
passive-title contract.  It does not contain balance values, trait effects, or
runtime dispatch.  It validates data supplied by the author before a dataset
is allowed to become a canonical runtime source.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import math
from typing import Any


SET2_ROSTER_SIZE = 32
SET2_COST_DISTRIBUTION = {1: 6, 2: 7, 3: 8, 4: 6, 5: 5}
SET2_TRAIT_COUNT = 12
SET2_REMOVED_TRAIT_NAMES = frozenset({"Żołnierz mentora"})
SET2_LIFECYCLE_TYPES = frozenset({"instant", "timed", "permanent", "periodic", "event_based"})
SET2_LIFECYCLE_REQUIRED_FIELDS = (
    "type",
    "activation",
    "duration",
    "duration_unit",
    "activation_delay",
    "activation_delay_unit",
    "refresh",
    "retrigger",
    "stacking",
    "expires_when",
)
SET2_PASSIVE_NAMES = {
    "anamol04": "Linijka z notatnika",
    "fiko": "Jajcarz",
    "uhla": "Hutnik, Hutnik to nasz klub",
    "szanowny_kantor": "Serial",
    "chessowy_mentos": "44 sekundy chwały",
    "yossarian": "Wysoki sądzie, to był tylko mały figiel",
    "galanonim": "Najlepszy przyjaciel Aleksandra",
    "pytl": "Taktyczna podwkurwka",
    "sofronow": "POwazna weryfikacja",
    "alyson_stark": "Waffen kindergarden",
    "skibidi_kubus": "Uszaty Gollum",
    "aus_sher": "Nieposkromiona adoracja",
    "szalwia": "Urocze stópki",
    "mr0czeq1": "Przekminka",
    "optimusprime": "Uprzejmie donoszę",
    "kotmarcek": "Ole ole Haxball wrze",
    "bbobel": "Młoda krew",
    "fallensmokk": "Archeologia",
    "jaeger": "Kryptonim Jeleń",
    "kaktusek": "Walkover",
    "empty_melancholy": "Oskarżony",
    "4tune": "Mściwa Edyta",
    "jadlainwestycji": "Inwestor 2137%",
    "boczek": "Erosoman",
    "merex": "nie",
    "marcel_galadotka": "Widz idealny",
    "klemens_zydoslawski": "Analiza <>",
    "nicosc": "Mogę unbana?",
    "knauff": "Nielot",
    "vitas": "Rozbudzenie zmysłów",
    "szachowymentor": "Arcyoferma",
    "9wojtaz9": "Jakiś ziomek",
}


def validate_active_set2_dataset(
    units: Any,
    traits: Any,
    *,
    expected_unit_count: int = SET2_ROSTER_SIZE,
    expected_trait_count: int | None = SET2_TRAIT_COUNT,
) -> list[str]:
    """Validate the complete dataset before it becomes active runtime data.

    The roster and trait validators intentionally remain independently useful
    for authoring fixtures.  Runtime loading also needs the cross-record
    invariant that every unit trait resolves to the same active trait source.
    """

    errors = [
        *validate_set2_roster(units, expected_count=expected_unit_count),
        *validate_set2_traits(traits, expected_count=expected_trait_count),
    ]

    trait_names = set()
    if isinstance(traits, Sequence) and not isinstance(traits, (str, bytes)):
        trait_names = {
            trait.get("name")
            for trait in traits
            if _is_object(trait) and _non_empty_string(trait.get("name"))
        }
    if isinstance(units, Sequence) and not isinstance(units, (str, bytes)):
        for index, unit in enumerate(units):
            if not _is_object(unit) or not isinstance(unit.get("traits"), list):
                continue
            for trait_name in unit["traits"]:
                if trait_name not in trait_names:
                    errors.append(
                        f"unit[{index}].traits references unknown active Set 2 trait: {trait_name!r}"
                    )

    # The exact title mapping is part of the active 32-unit author contract.
    # Keep the smaller fixture mode useful for structural tests and authoring
    # tools by applying this content check only to the full active dataset.
    if expected_unit_count == SET2_ROSTER_SIZE and expected_trait_count == SET2_TRAIT_COUNT:
        errors.extend(_validate_active_set2_passive_names(units))

    return errors


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_object(value: Any) -> bool:
    return isinstance(value, Mapping)


def _validate_active_set2_passive_names(records: Any) -> list[str]:
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return []

    errors: list[str] = []
    for index, record in enumerate(records):
        path = f"unit[{index}]"
        if not _is_object(record):
            continue

        unit_id = record.get("id")
        expected = SET2_PASSIVE_NAMES.get(unit_id)
        if expected is None:
            errors.append(f"{path} has no canonical active Set 2 passive title mapping for id {unit_id!r}")
            continue

        passive = record.get("passive")
        if not _is_object(passive):
            continue

        name = passive.get("name")
        title = passive.get("title")
        candidate = name if _non_empty_string(name) else title
        if not _non_empty_string(candidate):
            errors.append(f"{path}.passive must have a non-empty player-facing name or title")
            continue
        if _non_empty_string(name) and _non_empty_string(title) and name != title:
            errors.append(f"{path}.passive.name and .title must match")
        if candidate != expected:
            errors.append(
                f"{path}.passive title mismatch for {unit_id!r}: expected {expected!r}, got {candidate!r}"
            )
        if candidate == record.get("name"):
            errors.append(f"{path}.passive title must be independent from the unit name")

    return errors


def _validate_trait_effect_metadata(effect: Any, path: str) -> list[str]:
    """Validate the explicit lifecycle/value contract for active trait effects."""

    if not _is_object(effect):
        return []

    errors: list[str] = []
    lifecycle = effect.get("lifecycle")
    if not _is_object(lifecycle):
        errors.append(f"{path} missing required object 'lifecycle'")
    else:
        for field in SET2_LIFECYCLE_REQUIRED_FIELDS:
            if field not in lifecycle:
                errors.append(f"{path}.lifecycle missing required field '{field}'")

        lifecycle_type = lifecycle.get("type")
        if lifecycle_type not in SET2_LIFECYCLE_TYPES:
            errors.append(
                f"{path}.lifecycle.type must be one of {sorted(SET2_LIFECYCLE_TYPES)}"
            )

        for field in ("activation", "refresh", "retrigger", "stacking", "expires_when"):
            if field in lifecycle and not _non_empty_string(lifecycle.get(field)):
                errors.append(f"{path}.lifecycle.{field} must be a non-empty string")

        duration = lifecycle.get("duration")
        duration_unit = lifecycle.get("duration_unit")
        if duration is not None and (not _is_finite_number(duration) or duration <= 0):
            errors.append(f"{path}.lifecycle.duration must be null or a positive finite number")
        if duration is None and duration_unit is not None:
            errors.append(f"{path}.lifecycle.duration_unit must be null when duration is null")
        if duration is not None and duration_unit != "seconds":
            errors.append(f"{path}.lifecycle.duration_unit must be 'seconds' for a duration")
        if lifecycle_type == "timed" and duration is None:
            errors.append(f"{path}.lifecycle.duration is required for timed effects")

        activation_delay = lifecycle.get("activation_delay")
        activation_delay_unit = lifecycle.get("activation_delay_unit")
        if activation_delay is not None and (not _is_finite_number(activation_delay) or activation_delay < 0):
            errors.append(
                f"{path}.lifecycle.activation_delay must be null or a non-negative finite number"
            )
        if activation_delay is None and activation_delay_unit is not None:
            errors.append(
                f"{path}.lifecycle.activation_delay_unit must be null when activation_delay is null"
            )
        if activation_delay is not None and activation_delay_unit != "seconds":
            errors.append(
                f"{path}.lifecycle.activation_delay_unit must be 'seconds' for an activation delay"
            )

    authored_effect = effect.get("effect")
    if not _is_object(authored_effect):
        return errors

    value = authored_effect.get("value")
    if not _is_finite_number(value):
        errors.append(f"{path}.effect.value must be a finite number")

    if not _non_empty_string(authored_effect.get("value_unit")):
        errors.append(f"{path}.effect.value_unit must be a non-empty string")

    values = authored_effect.get("values")
    if not isinstance(values, list) or not values:
        errors.append(f"{path}.effect.values must be a non-empty list")
    else:
        for value_index, value_detail in enumerate(values):
            value_path = f"{path}.effect.values[{value_index}]"
            if not _is_object(value_detail):
                errors.append(f"{value_path} must be an object")
                continue
            for field in ("key", "unit"):
                if not _non_empty_string(value_detail.get(field)):
                    errors.append(f"{value_path}.{field} must be a non-empty string")
            if not _is_finite_number(value_detail.get("value")):
                errors.append(f"{value_path}.value must be a finite number")

        first_value = values[0]
        if _is_object(first_value):
            if _is_finite_number(value) and first_value.get("value") != value:
                errors.append(f"{path}.effect.values[0].value must match effect.value")
            if (
                _non_empty_string(authored_effect.get("value_unit"))
                and first_value.get("unit") != authored_effect.get("value_unit")
            ):
                errors.append(f"{path}.effect.values[0].unit must match effect.value_unit")

    if _is_object(lifecycle) and _is_object(effect.get("limit")):
        if lifecycle.get("stacking") != effect["limit"].get("stacking"):
            errors.append(f"{path}.lifecycle.stacking must match {path}.limit.stacking")

    return errors


def _validate_modular_effect(effect: Any, path: str, *, require_trait_metadata: bool = False) -> list[str]:
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

    if require_trait_metadata:
        errors.extend(_validate_trait_effect_metadata(effect, path))

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
                        require_trait_metadata=True,
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
