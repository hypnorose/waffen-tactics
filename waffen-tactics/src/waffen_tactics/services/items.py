"""Canonical item definitions and two-component recipes.

The approved WFT-139 matrix is the only content source used by the runtime.
This module deliberately fails closed when the source is missing, malformed,
or no longer carries the accepted contract.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from .item_contract import validate_item_matrix


MATRIX_PATH = Path(__file__).resolve().parents[3] / "item_recipe_matrix_wft139.json"
EXPECTED_MATRIX_ID = "WFT-139"
EXPECTED_MATRIX_STATUS = "approved-runtime-contract"


class ItemSourceError(ValueError):
    """Raised when the approved item source cannot be activated safely."""


LEGACY_ITEM_IDS = frozenset({"sugar_rush", "seasoned_armor", "contraband"})


def validate_persistent_item_ids(
    item_ids: Any,
    location: str,
    *,
    max_count: int | None = None,
) -> None:
    """Validate item IDs at a durable player-state boundary.

    Inventory and equipped loadout are the only persistent item state.  This
    deliberately rejects stale/legacy IDs instead of dropping or remapping
    them, because a partial loadout would silently change gameplay.
    """

    if not isinstance(item_ids, list):
        raise ItemSourceError(f"Persistent item state {location} must be a list")
    if max_count is not None and len(item_ids) > max_count:
        raise ItemSourceError(
            f"Persistent item state {location} exceeds the {max_count}-item limit"
        )

    for index, item_id in enumerate(item_ids):
        if not isinstance(item_id, str) or item_id not in ITEMS:
            if isinstance(item_id, str) and item_id in LEGACY_ITEM_IDS:
                raise ItemSourceError(
                    f"Legacy item ID at {location}[{index}] is not in the approved WFT-139 catalog: {item_id!r}"
                )
            raise ItemSourceError(
                f"Unknown persistent item ID at {location}[{index}]: {item_id!r}"
            )


def _load_approved_matrix() -> dict[str, Any]:
    with MATRIX_PATH.open(encoding="utf-8") as handle:
        matrix = json.load(handle)

    if not isinstance(matrix, dict):
        raise ItemSourceError("WFT-139 item source must be an object")
    if matrix.get("matrix_id") != EXPECTED_MATRIX_ID:
        raise ItemSourceError("Unexpected item matrix identity")
    if matrix.get("status") != EXPECTED_MATRIX_STATUS:
        raise ItemSourceError("WFT-139 item matrix is not approved for runtime")

    base_items = matrix.get("base_items")
    recipes = matrix.get("recipes")
    if not isinstance(base_items, list) or not isinstance(recipes, list):
        raise ItemSourceError("WFT-139 item matrix must contain base_items and recipes lists")

    records = [*base_items, *recipes]
    validate_item_matrix(records)
    return matrix


def _runtime_item(record: Mapping[str, Any]) -> dict[str, Any]:
    item = copy.deepcopy(dict(record))
    if item["kind"] == "combined":
        # Keep the API-compatible description while preserving the complete
        # structured effect contract for future combat/replay wiring.
        item["description"] = item["effect"]["description"]
    return item


_MATRIX = _load_approved_matrix()
BASE_ITEMS = {
    item["id"]: _runtime_item(item)
    for item in _MATRIX["base_items"]
}
_RECIPES = {
    tuple(sorted(recipe["components"])): (
        recipe["id"],
        recipe["name"],
        copy.deepcopy(recipe["stats"]),
        recipe["effect_description"],
    )
    for recipe in _MATRIX["recipes"]
}
ITEMS = {
    item["id"]: _runtime_item(item)
    for item in [*_MATRIX["base_items"], *(_MATRIX["recipes"])]
}
RECIPES = {pair: value[0] for pair, value in _RECIPES.items()}


def apply_item_stats(base_stats: Mapping[str, float], item_ids: list[str] | tuple[str, ...]) -> dict[str, float]:
    """Apply equipped item stat packages through one shared contract.

    Unknown item IDs are rejected instead of being silently ignored, so a
    stale save cannot produce a partially buffed combat or UI projection.
    """

    updated = dict(base_stats)
    for item_id in item_ids:
        if not isinstance(item_id, str) or item_id not in ITEMS:
            raise ItemSourceError(f"Unknown equipped item: {item_id!r}")
        for stat, value in ITEMS[item_id]["stats"].items():
            updated[stat] = updated.get(stat, 0) + value
    return updated


def item_payload(item_id: str) -> dict[str, Any]:
    return {"id": item_id, **copy.deepcopy(ITEMS[item_id])}


def all_item_payloads() -> list[dict[str, Any]]:
    return [item_payload(item_id) for item_id in ITEMS]


def combine_item_ids(first: Any, second: Any) -> str | None:
    """Return the canonical result for a legal unordered pair, or ``None``."""

    if not isinstance(first, str) or not isinstance(second, str):
        return None
    if first not in BASE_ITEMS or second not in BASE_ITEMS:
        return None
    return RECIPES.get(tuple(sorted((first, second))))
