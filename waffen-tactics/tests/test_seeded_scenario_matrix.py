import json
from pathlib import Path

from waffen_tactics.services.passive_definitions import PASSIVE_DEFINITIONS


MATRIX = Path(__file__).resolve().parents[2] / "docs" / "SEEDED_SCENARIO_MATRIX_2026-09-09.json"
REPO_ROOT = MATRIX.parents[1]


def test_seeded_scenario_matrix_is_complete_and_reproducible_by_reference():
    with MATRIX.open(encoding="utf-8") as handle:
        matrix = json.load(handle)

    scenarios = matrix["scenarios"]
    seeds = [scenario["seed"] for scenario in scenarios]
    assert len(seeds) == len(set(seeds))
    assert all(isinstance(seed, int) and seed > 0 for seed in seeds)

    for scenario in scenarios:
        assert scenario["id"]
        assert scenario["team_a"]
        assert scenario["team_b"]
        assert scenario["formation"]["team_a"]
        assert scenario["formation"]["team_b"]
        assert scenario["expected"]
        assert scenario["acceptance"]
        coverage = scenario.get("coverage", {})
        assert coverage.get("positive"), f"Missing positive coverage contract: {scenario['id']}"
        assert coverage.get("negative") or coverage.get("boundary"), (
            f"Missing negative/boundary coverage contract: {scenario['id']}"
        )
        reference = scenario["test_reference"].split("::", 1)[0]
        assert (REPO_ROOT / reference).exists(), f"Missing runner reference: {reference}"

    replay = next(item for item in scenarios if item["id"] == "canonical_replay_snapshot_parity")
    assert replay["expected"]["snapshot_desyncs"] == 0
    assert (REPO_ROOT / replay["test_reference"]).exists()

    passive_matrix = next(item for item in scenarios if item["id"] == "canonical_passive_seeded_matrix")
    assert passive_matrix["expected"]["deterministic"] is True
    assert passive_matrix["expected"]["passive_definitions"] == len(PASSIVE_DEFINITIONS)

    trait_matrix = next(item for item in scenarios if item["id"] == "canonical_trait_threshold_matrix")
    assert trait_matrix["expected"]["deterministic"] is True
    with (REPO_ROOT / "waffen-tactics" / "traits.json").open(encoding="utf-8") as handle:
        canonical_traits = json.load(handle)["traits"]
    assert trait_matrix["expected"]["trait_count"] == len(canonical_traits)

    family_matrix = next(item for item in scenarios if item["id"] == "canonical_passive_trigger_family_matrix")
    canonical_families = sorted({definition["kind"] for definition in PASSIVE_DEFINITIONS.values()})
    assert family_matrix["expected"]["trigger_families"] == canonical_families
    assert family_matrix["expected"]["positive_and_negative_paths"] is True
