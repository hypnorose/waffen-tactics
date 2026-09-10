"""Fail-closed validation for the author-approved Set 2 item matrix.

This module intentionally validates a supplied matrix without defining any
item names, stats, or effects.  The authored matrix remains the source of
truth; this is only the technical boundary that prevents implicit content or
runtime assumptions from entering the pipeline.
"""

from collections.abc import Mapping, Sequence
from itertools import combinations_with_replacement
from math import isfinite
from typing import Any


EXPECTED_BASE_ITEM_COUNT = 6
EXPECTED_COMBINED_ITEM_COUNT = 21

ITEM_REQUIRED_FIELDS = frozenset(
    {
        "id",
        "name",
        "kind",
        "components",
        "stats",
        "effect",
        "content_version",
    }
)
EFFECT_REQUIRED_FIELDS = frozenset(
    {
        "family",
        "description",
        "trigger",
        "target",
        "scope",
        "order",
        "duration",
        "stacking",
        "cap",
        "reset_between_fights",
        "rng",
        "replay",
    }
)
RNG_REQUIRED_FIELDS = frozenset({"mode", "seed"})
REPLAY_REQUIRED_FIELDS = frozenset({"mode", "event_types"})
STACKING_REQUIRED_FIELDS = frozenset({"mode", "max_stacks"})


class ItemContractError(ValueError):
    """Raised when a Set 2 item matrix is incomplete or ambiguous."""

    def __init__(self, errors: Sequence[str]):
        self.errors = tuple(errors)
        super().__init__("Item contract validation failed: " + "; ".join(self.errors))


def validate_item_matrix(items: Sequence[Mapping[str, Any]]) -> None:
    """Validate the complete Set 2 matrix and raise on the first boundary breach.

    The validator is deliberately data-agnostic.  It accepts author-provided
    names, stats, and effect values, while requiring every field needed by
    runtime, replay, and player-facing presentation to be explicit.
    """

    errors: list[str] = []
    if isinstance(items, (str, bytes)) or not isinstance(items, Sequence):
        raise ItemContractError(["matrix must be a sequence of item records"])

    records = list(items)
    ids: list[str] = []
    base_ids: list[str] = []
    combined_pairs: dict[tuple[str, str], str] = {}

    for index, item in enumerate(records):
        path = f"items[{index}]"
        if not isinstance(item, Mapping):
            errors.append(f"{path} must be an object")
            continue

        missing = sorted(ITEM_REQUIRED_FIELDS - item.keys())
        if missing:
            errors.append(f"{path} missing required fields: {', '.join(missing)}")

        item_id = item.get("id")
        if not _non_empty_string(item_id):
            errors.append(f"{path}.id must be a non-empty string")
        else:
            ids.append(item_id)

        if not _non_empty_string(item.get("name")):
            errors.append(f"{path}.name must be a non-empty string")
        if not _non_empty_string(item.get("content_version")):
            errors.append(f"{path}.content_version must be a non-empty string")

        kind = item.get("kind")
        if kind not in {"base", "combined"}:
            errors.append(f"{path}.kind must be 'base' or 'combined'")

        components = item.get("components")
        if not isinstance(components, list):
            errors.append(f"{path}.components must be a list")
        elif kind == "base" and components:
            errors.append(f"{path}.components must be empty for a base item")
        elif kind == "combined":
            if len(components) != 2:
                errors.append(f"{path}.components must contain exactly two base IDs")
            elif not all(_non_empty_string(component) for component in components):
                errors.append(f"{path}.components must contain non-empty string IDs")
            elif _non_empty_string(item_id):
                pair = tuple(sorted(components))
                if pair in combined_pairs:
                    errors.append(
                        f"{path} duplicates recipe pair {pair} already used by "
                        f"{combined_pairs[pair]}"
                    )
                else:
                    combined_pairs[pair] = item_id

        stats = item.get("stats")
        if not isinstance(stats, Mapping) or not stats:
            errors.append(f"{path}.stats must be a non-empty object")
        elif any(
            not _finite_number(value)
            for value in stats.values()
        ):
            errors.append(f"{path}.stats values must be finite numbers")

        effect = item.get("effect")
        if kind == "base" and "effect" in item and effect is not None:
            errors.append(f"{path}.effect must be null for a base item")
        if kind == "combined" and not isinstance(effect, Mapping):
            errors.append(f"{path}.effect must be an explicit object for a combined item")
        elif isinstance(effect, Mapping):
            errors.extend(_validate_effect(effect, path + ".effect"))

        if kind == "base" and _non_empty_string(item_id):
            base_ids.append(item_id)

    _append_duplicate_errors(ids, "item IDs", errors)
    if len(base_ids) != EXPECTED_BASE_ITEM_COUNT:
        errors.append(
            f"base item count must be {EXPECTED_BASE_ITEM_COUNT}, got {len(base_ids)}"
        )

    if len(combined_pairs) != EXPECTED_COMBINED_ITEM_COUNT:
        errors.append(
            "combined recipe count must be "
            f"{EXPECTED_COMBINED_ITEM_COUNT}, got {len(combined_pairs)}"
        )

    if len(base_ids) == EXPECTED_BASE_ITEM_COUNT and len(set(base_ids)) == len(base_ids):
        expected_pairs = {
            tuple(sorted(pair))
            for pair in combinations_with_replacement(base_ids, 2)
        }
        actual_pairs = set(combined_pairs)
        for pair in sorted(expected_pairs - actual_pairs):
            errors.append(f"missing explicit recipe pair {pair}")
        for pair in sorted(actual_pairs - expected_pairs):
            errors.append(f"recipe pair {pair} references an unknown base ID")

    if errors:
        raise ItemContractError(errors)


def _validate_effect(effect: Mapping[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    missing = sorted(EFFECT_REQUIRED_FIELDS - effect.keys())
    if missing:
        errors.append(f"{path} missing required fields: {', '.join(missing)}")

    for field in ("family", "description", "trigger", "target", "scope", "order"):
        if not _non_empty_string(effect.get(field)):
            errors.append(f"{path}.{field} must be a non-empty string")

    duration = effect.get("duration")
    if duration is not None and not _non_negative_finite_number(duration):
        errors.append(f"{path}.duration must be null or a non-negative finite number")

    stacking = effect.get("stacking")
    if not isinstance(stacking, Mapping):
        errors.append(f"{path}.stacking must be an explicit object")
    else:
        missing_stacking = sorted(STACKING_REQUIRED_FIELDS - stacking.keys())
        if missing_stacking:
            errors.append(
                f"{path}.stacking missing required fields: {', '.join(missing_stacking)}"
            )
        if not _non_empty_string(stacking.get("mode")):
            errors.append(f"{path}.stacking.mode must be a non-empty string")
        max_stacks = stacking.get("max_stacks")
        if not isinstance(max_stacks, int) or isinstance(max_stacks, bool) or max_stacks < 1:
            errors.append(f"{path}.stacking.max_stacks must be a positive integer")

    if not isinstance(effect.get("reset_between_fights"), bool):
        errors.append(f"{path}.reset_between_fights must be a boolean")

    rng = effect.get("rng")
    if not isinstance(rng, Mapping):
        errors.append(f"{path}.rng must be an explicit object")
    else:
        missing_rng = sorted(RNG_REQUIRED_FIELDS - rng.keys())
        if missing_rng:
            errors.append(f"{path}.rng missing required fields: {', '.join(missing_rng)}")
        if not _non_empty_string(rng.get("mode")):
            errors.append(f"{path}.rng.mode must be a non-empty string")

    replay = effect.get("replay")
    if not isinstance(replay, Mapping):
        errors.append(f"{path}.replay must be an explicit object")
    else:
        missing_replay = sorted(REPLAY_REQUIRED_FIELDS - replay.keys())
        if missing_replay:
            errors.append(
                f"{path}.replay missing required fields: {', '.join(missing_replay)}"
            )
        if not _non_empty_string(replay.get("mode")):
            errors.append(f"{path}.replay.mode must be a non-empty string")
        event_types = replay.get("event_types")
        if (
            not isinstance(event_types, list)
            or not event_types
            or not all(_non_empty_string(event_type) for event_type in event_types)
        ):
            errors.append(f"{path}.replay.event_types must be a non-empty string list")

    return errors


def _append_duplicate_errors(values: Sequence[str], label: str, errors: list[str]) -> None:
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        errors.append(f"duplicate {label}: {', '.join(duplicates)}")


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _non_negative_finite_number(value: Any) -> bool:
    return _finite_number(value) and value >= 0
