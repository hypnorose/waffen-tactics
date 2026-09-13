"""WFT-217 backend/API coverage for the complete active Set 2 trait matrix."""

from __future__ import annotations

import json
from pathlib import Path

from routes.game_data import get_traits_data


REPO_ROOT = Path(__file__).resolve().parents[3]
REQUIRED_LIFECYCLE_FIELDS = {
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
}


def _canonical_traits() -> list[dict]:
    return json.loads(
        (REPO_ROOT / "waffen-tactics" / "traits.json").read_text(encoding="utf-8")
    )["traits"]


def _assert_complete_trait_matrix(payload: list[dict], canonical: list[dict]) -> None:
    assert len(payload) == 12
    assert {trait["name"] for trait in payload} == {trait["name"] for trait in canonical}

    canonical_by_name = {trait["name"]: trait for trait in canonical}
    effect_count = 0
    for trait in payload:
        source = canonical_by_name[trait["name"]]
        for field in (
            "id",
            "name",
            "type",
            "description",
            "target",
            "thresholds",
            "threshold_descriptions",
            "modular_effects",
        ):
            assert trait[field] == source[field], f"{trait['name']} lost canonical field {field}"

        assert len(trait["thresholds"]) == len(trait["threshold_descriptions"]) == len(trait["modular_effects"])
        assert all("<" not in description and ">" not in description for description in trait["threshold_descriptions"])
        for tier in trait["modular_effects"]:
            for effect in tier:
                effect_count += 1
                assert set(REQUIRED_LIFECYCLE_FIELDS) <= set(effect["lifecycle"])
                assert effect["effect"]["values"]
                assert effect["effect"]["values"][0]["value"] == effect["effect"]["value"]
                assert effect["effect"]["values"][0]["unit"] == effect["effect"]["value_unit"]

    assert effect_count == 32


def test_game_traits_endpoint_preserves_the_complete_canonical_matrix(client):
    canonical = _canonical_traits()
    response = client.get("/game/traits")

    assert response.status_code == 200
    payload = response.get_json()
    _assert_complete_trait_matrix(payload, canonical)


def test_get_traits_data_preserves_canonical_matrix_before_json_serialization():
    canonical = _canonical_traits()
    _assert_complete_trait_matrix(get_traits_data(), canonical)
