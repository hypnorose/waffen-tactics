"""Validation for the structured combat snapshot contract.

Snapshots are validation and transport data, not a place to recover from a
broken event stream.  Keep this contract deliberately strict so a producer
cannot turn a unit or one of its collections into a display string and still
produce a superficially valid replay log.
"""

import json
import math
from typing import Any, Dict


class CombatSnapshotContractError(ValueError):
    """Raised when a combat snapshot is not structurally JSON-safe."""


_REQUIRED_UNIT_FIELDS = (
    "id",
    "hp",
    "max_hp",
    "current_mana",
    "max_mana",
    "shield",
    "effects",
)
_NUMERIC_UNIT_FIELDS = (
    "hp",
    "max_hp",
    "current_mana",
    "max_mana",
    "shield",
)
_STRUCTURED_UNIT_FIELDS = (
    "buffed_stats",
    "base_stats",
    "item_runtime_state",
    "passive",
)


def _fail(context: str, field: str, expected: str, actual: Any) -> None:
    actual_type = type(actual).__name__
    raise CombatSnapshotContractError(
        f"Invalid combat snapshot at {context}: field={field}; "
        f"expected {expected}, got {actual_type}"
    )


def _require_finite_number(value: Any, context: str, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(context, field, "a finite number", value)
    if not math.isfinite(float(value)):
        _fail(context, field, "a finite number", value)


def _validate_effect(effect: Any, context: str, index: int) -> None:
    field = f"{context}.effects[{index}]"
    if not isinstance(effect, dict):
        _fail(context, field, "an object", effect)
    effect_id = effect.get("id")
    if not isinstance(effect_id, str) or not effect_id.strip():
        _fail(context, f"{field}.id", "a non-empty string effect_id", effect_id)


def validate_combat_snapshot(snapshot: Any, *, context: str = "snapshot") -> Dict[str, Any]:
    """Validate and return a structured combat snapshot.

    The returned object is the original value; callers decide whether they
    need a deep copy.  The function rejects stringified units, stringified
    arrays, malformed nested effects, missing canonical combat resources, and
    non-finite numeric values.  It intentionally does not parse or coerce
    anything.
    """
    if not isinstance(snapshot, dict):
        _fail(context, "snapshot", "an object", snapshot)

    for side in ("player_units", "opponent_units"):
        units = snapshot.get(side)
        if not isinstance(units, list):
            _fail(context, side, "an array of unit objects", units)

        for index, unit in enumerate(units):
            unit_context = f"{context}.{side}[{index}]"
            if not isinstance(unit, dict):
                _fail(context, unit_context, "an object", unit)

            for field in _REQUIRED_UNIT_FIELDS:
                if field not in unit:
                    _fail(context, f"{unit_context}.{field}", "a present canonical field", None)

            if not isinstance(unit.get("id"), str) or not unit["id"].strip():
                _fail(context, f"{unit_context}.id", "a non-empty string", unit.get("id"))

            for field in _NUMERIC_UNIT_FIELDS:
                _require_finite_number(unit.get(field), context, f"{unit_context}.{field}")

            effects = unit.get("effects")
            if not isinstance(effects, list):
                _fail(context, f"{unit_context}.effects", "an array of effect objects", effects)
            for effect_index, effect in enumerate(effects):
                _validate_effect(effect, unit_context, effect_index)

            for field in _STRUCTURED_UNIT_FIELDS:
                value = unit.get(field)
                if value is None:
                    continue
                if not isinstance(value, dict):
                    _fail(context, f"{unit_context}.{field}", "an object", value)

    return snapshot


def dumps_combat_snapshot(snapshot: Any, *, context: str = "snapshot") -> str:
    """Validate, serialize, and validate the JSON round-trip."""
    validate_combat_snapshot(snapshot, context=context)
    try:
        encoded = json.dumps(snapshot, ensure_ascii=False, allow_nan=False)
        decoded = json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise CombatSnapshotContractError(
            f"Invalid combat snapshot at {context}: JSON serialization failed"
        ) from exc
    validate_combat_snapshot(decoded, context=f"{context} after JSON round-trip")
    return encoded
