"""WFT-217 executable matrix for the active author-approved Set 2 traits."""

from __future__ import annotations

import json
from pathlib import Path

from waffen_tactics.services.set2_contract import validate_set2_traits


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TRAITS = {
    "Konfident",
    "Wierny widz",
    "Nowociota",
    "Figlarz",
    "Weeb",
    "Starociota",
    "Inwestor",
    "Femboy",
    "Szachista",
    "Twórca",
    "Muzyk",
    "Haxball",
}
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


def _active_traits() -> list[dict]:
    return json.loads(
        (ROOT / "traits.json").read_text(encoding="utf-8")
    )["traits"]


def test_active_set2_trait_matrix_covers_every_tier_and_effect_contract():
    traits = _active_traits()

    assert validate_set2_traits(traits) == []
    assert {trait["name"] for trait in traits} == EXPECTED_TRAITS

    effect_count = 0
    for trait in traits:
        tiers = trait["modular_effects"]
        assert len(tiers) == len(trait["thresholds"]), trait["name"]
        assert len(trait["threshold_descriptions"]) == len(tiers), trait["name"]

        for tier_index, tier in enumerate(tiers, start=1):
            assert tier, f"{trait['name']} tier {tier_index} has no effects"
            for effect in tier:
                effect_count += 1
                assert {"trigger", "conditions", "target", "effect", "lifecycle", "limit"} <= set(effect)
                assert effect["trigger"]
                assert effect["target"]
                assert isinstance(effect["conditions"], dict)

                authored = effect["effect"]
                assert authored["trait"] == trait["name"]
                assert authored["tier"] == tier_index
                assert isinstance(authored["value"], (int, float))
                assert authored["value_unit"]
                assert authored["values"]
                assert authored["values"][0]["value"] == authored["value"]
                assert authored["values"][0]["unit"] == authored["value_unit"]

                lifecycle = effect["lifecycle"]
                assert set(lifecycle) == REQUIRED_LIFECYCLE_FIELDS
                assert lifecycle["type"]
                assert lifecycle["activation"]
                assert lifecycle["refresh"]
                assert lifecycle["retrigger"]
                assert lifecycle["expires_when"]
                assert lifecycle["stacking"] == effect["limit"]["stacking"]

        for description in trait["threshold_descriptions"]:
            assert isinstance(description, str) and description.strip()
            assert "<" not in description and ">" not in description

    assert effect_count == 32
