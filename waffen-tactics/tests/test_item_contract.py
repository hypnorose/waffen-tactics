import copy

import pytest

from waffen_tactics.services.item_contract import ItemContractError, validate_item_matrix


BASE_IDS = ["base_a", "base_b", "base_c", "base_d", "base_e", "base_f"]


def _effect():
    return {
        "family": "synthetic",
        "description": "Synthetic contract fixture; not approved content.",
        "trigger": "on_explicit_test_event",
        "target": "owner",
        "scope": "self",
        "order": "after_canonical_event",
        "duration": None,
        "stacking": {"mode": "refresh", "max_stacks": 1},
        "cap": None,
        "reset_between_fights": True,
        "rng": {"mode": "none", "seed": None},
        "replay": {"mode": "canonical_event", "event_types": ["item_effect"]},
    }


def _valid_matrix():
    records = [
        {
            "id": item_id,
            "name": f"Synthetic {item_id}",
            "kind": "base",
            "components": [],
            "stats": {"attack": 1},
            "effect": None,
            "content_version": "set2-draft",
        }
        for item_id in BASE_IDS
    ]
    for left_index, left in enumerate(BASE_IDS):
        for right in BASE_IDS[left_index:]:
            records.append(
                {
                    "id": f"combined_{left}_{right}",
                    "name": f"Synthetic {left}+{right}",
                    "kind": "combined",
                    "components": [left, right],
                    "stats": {"attack": 2},
                    "effect": _effect(),
                    "content_version": "set2-draft",
                }
            )
    return records


def test_valid_matrix_has_explicit_contract_for_all_six_bases_and_21_recipes():
    validate_item_matrix(_valid_matrix())


def test_contract_rejects_missing_effect_field_before_runtime_can_infer_it():
    matrix = _valid_matrix()
    del matrix[-1]["effect"]["replay"]

    with pytest.raises(ItemContractError, match=r"replay"):
        validate_item_matrix(matrix)


def test_contract_rejects_missing_a_plus_a_recipe():
    matrix = _valid_matrix()
    matrix.pop()

    with pytest.raises(ItemContractError, match=r"combined recipe count|missing explicit recipe pair"):
        validate_item_matrix(matrix)


def test_contract_rejects_duplicate_pair_and_unknown_component():
    matrix = _valid_matrix()
    duplicate = copy.deepcopy(matrix[-1])
    duplicate["id"] = "combined_duplicate"
    duplicate["components"] = ["base_a", "base_b"]
    matrix.append(duplicate)

    with pytest.raises(ItemContractError, match=r"duplicates recipe pair|combined recipe count"):
        validate_item_matrix(matrix)

    matrix = _valid_matrix()
    matrix[-1]["components"] = ["base_a", "not_a_base"]
    with pytest.raises(ItemContractError, match=r"unknown base ID|missing explicit recipe pair"):
        validate_item_matrix(matrix)


def test_contract_rejects_non_object_records_fail_closed():
    matrix = _valid_matrix()
    matrix[0] = None

    with pytest.raises(ItemContractError, match=r"items\[0\] must be an object"):
        validate_item_matrix(matrix)


def test_contract_rejects_non_null_effect_on_base_item():
    matrix = _valid_matrix()
    matrix[0]["effect"] = _effect()

    with pytest.raises(ItemContractError, match=r"effect must be null for a base item"):
        validate_item_matrix(matrix)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("family", "", "family must be a non-empty string"),
        ("duration", -1, "duration must be null or a non-negative finite number"),
        ("stacking", {"mode": "refresh"}, "stacking missing required fields"),
        ("stacking", {"mode": "refresh", "max_stacks": 0}, "max_stacks must be a positive integer"),
    ],
)
def test_contract_rejects_implicit_or_invalid_effect_runtime_fields(field, value, message):
    matrix = _valid_matrix()
    matrix[-1]["effect"][field] = value

    with pytest.raises(ItemContractError, match=message):
        validate_item_matrix(matrix)
