"""Build the deterministic seeded-coverage report from canonical data.

The report is an audit artifact, not a second source of combat rules.  It
only joins canonical data counts with the executable scenario references in
the versioned matrix and keeps automated evidence separate from manual
runtime acceptance.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "waffen-tactics" / "src"
MATRIX_PATH = ROOT / "docs" / "SEEDED_SCENARIO_MATRIX_2026-09-09.json"
REPORT_PATH = ROOT / "docs" / "SEEDED_SCENARIO_COVERAGE_REPORT_2026-09-10.json"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from waffen_tactics.services.passive_definitions import PASSIVE_DEFINITIONS  # noqa: E402


UNIT_TEST_REFERENCE = (
    "waffen-tactics/tests/test_canonical_seeded_matrix.py::"
    "test_passive_matrix_replays_every_canonical_definition_deterministically"
)
TRAIT_TEST_REFERENCE = (
    "waffen-tactics/tests/test_canonical_seeded_matrix.py::"
    "test_trait_threshold_matrix_covers_below_exact_and_next_boundary"
)
FAMILY_TEST_REFERENCE = (
    "waffen-tactics/tests/test_canonical_seeded_matrix.py::"
    "test_passive_trigger_family_matrix_has_positive_and_negative_path"
)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _scenario_map(matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {scenario["id"]: scenario for scenario in matrix["scenarios"]}


def _reference_path(reference: str) -> str:
    return reference.split("::", 1)[0]


def build_report() -> dict[str, Any]:
    units = _load_json(ROOT / "waffen-tactics" / "units.json")["units"]
    traits = _load_json(ROOT / "waffen-tactics" / "traits.json")["traits"]
    matrix = _load_json(MATRIX_PATH)
    scenarios = _scenario_map(matrix)

    unit_ids = sorted(unit["id"] for unit in units)
    passive_ids = sorted(PASSIVE_DEFINITIONS)
    trait_names = sorted(trait["name"] for trait in traits)
    trigger_families = sorted({definition["kind"] for definition in PASSIVE_DEFINITIONS.values()})

    edge_case_ids = [
        "frontline_then_backline",
        "no_legal_target_noop",
        "team_a_before_team_b_same_tick",
        "full_tempo_bonus_attack",
        "enemy_death_trigger",
        "ally_death_trigger_once",
        "low_hp_threshold",
    ]
    cross_layer_id = "canonical_replay_snapshot_parity"

    def scenario_evidence(scenario_id: str) -> dict[str, Any]:
        scenario = scenarios[scenario_id]
        return {
            "scenario_id": scenario_id,
            "seed": scenario["seed"],
            "test_reference": scenario["test_reference"],
            "fixture_or_runner": _reference_path(scenario["test_reference"]),
        }

    report = {
        "schema_version": 1,
        "source_of_truth": [
            "waffen-tactics/units.json",
            "waffen-tactics/traits.json",
            "waffen-tactics/src/waffen_tactics/services/passive_definitions.py",
            "docs/SEEDED_SCENARIO_MATRIX_2026-09-09.json",
        ],
        "generated_by": "tools/seeded_coverage_report.py",
        "automated_evidence_only": True,
        "canonical_counts": {
            "units": len(unit_ids),
            "passive_definitions": len(passive_ids),
            "traits": len(trait_names),
            "trigger_families": len(trigger_families),
            "matrix_scenarios": len(matrix["scenarios"]),
        },
        "failure_domains": {
            "data": {
                "status": "automated_contract",
                "reference": "waffen-tactics/units.json + traits.json + passive_definitions.py",
                "scope": "canonical IDs, counts, descriptions, and unit/passive alignment",
            },
            "runtime": {
                "status": "automated_contract",
                "reference": "waffen-tactics/tests/test_canonical_seeded_matrix.py",
                "scope": "seeded shared-core replay and trigger-family execution",
            },
            "emitter": {
                "status": "automated_contract",
                "reference": "waffen-tactics/tests/test_golden_replay_contract.py",
                "scope": "ordered canonical event stream and authoritative event payloads",
            },
            "reconstructor": {
                "status": "automated_contract",
                "reference": "waffen-tactics-web/backend/tests/test_golden_replay_contract.py",
                "scope": "backend event reconstruction against the approved snapshot",
            },
            "ui": {
                "status": "automated_contract",
                "reference": "waffen-tactics-web/src/hooks/combat/__tests__/realEventReplay.test.ts",
                "scope": "frontend replay and snapshot desync detection",
            },
        },
        "coverage": {
            "unit": {
                "status": "automated_evidence",
                "canonical_count": len(unit_ids),
                "covered_count": len(set(unit_ids) & set(passive_ids)),
                "uncovered_ids": sorted(set(unit_ids) - set(passive_ids)),
                "passive_ids_without_unit": sorted(set(passive_ids) - set(unit_ids)),
                "test_reference": UNIT_TEST_REFERENCE,
                "evidence": "One deterministic shared-simulator replay is executed for every canonical passive keyed by unit ID.",
            },
            "trait": {
                "status": "automated_evidence",
                "canonical_count": len(trait_names),
                "covered_count": len(trait_names),
                "trait_names": trait_names,
                "boundary_states": ["below", "exact", "next"],
                "test_reference": TRAIT_TEST_REFERENCE,
                "evidence": "Every canonical trait tier is exercised below threshold, at threshold, and at the next threshold where present.",
            },
            "trigger_family": {
                "status": "automated_evidence",
                "canonical_count": len(trigger_families),
                "covered_count": len(trigger_families),
                "families": trigger_families,
                "positive_and_negative_paths": True,
                "test_reference": FAMILY_TEST_REFERENCE,
                "evidence": "One explicit runtime representative provides a positive and negative or boundary path for every loaded family.",
            },
            "edge_case": {
                "status": "automated_evidence",
                "canonical_count": len(edge_case_ids),
                "covered_count": len(edge_case_ids),
                "scenarios": [scenario_evidence(scenario_id) for scenario_id in edge_case_ids],
                "evidence": "The seeded matrix includes targeting, no-target, ordering, full-mana, death, trigger-once, and HP-threshold boundaries.",
            },
            "cross_layer_replay": {
                "status": "automated_evidence",
                "layers": {
                    "data": "waffen-tactics-web/backend/test_fixtures/approved_replay_golden.json",
                    "runtime": "waffen-tactics/tests/test_golden_replay_contract.py",
                    "emitter": "waffen-tactics/tests/test_golden_replay_contract.py",
                    "reconstructor": "waffen-tactics-web/backend/tests/test_golden_replay_contract.py",
                    "ui": "waffen-tactics-web/src/hooks/combat/__tests__/realEventReplay.test.ts",
                },
                "evidence": scenario_evidence(cross_layer_id),
                "missing_event_fails": scenarios[cross_layer_id]["expected"]["missing_event_fails"],
            },
        },
        "manual_runtime": {
            "status": "pending",
            "required_evidence": [
                "authenticated Game View at 1280x720",
                "authenticated Game View at 1920x1080",
                "live combat and replay readability",
                "post-deploy VPS status and logs",
                "rollback evidence for the approved revision",
            ],
            "not_proven_by": ["pytest", "frontend tests", "typecheck", "lint", "production build"],
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    parser.add_argument("--check", action="store_true", help="fail if the checked-in report is stale")
    args = parser.parse_args()

    expected = build_report()
    if args.check:
        if not args.output.exists():
            print(f"missing report: {args.output}", file=sys.stderr)
            return 1
        actual = _load_json(args.output)
        if actual != expected:
            print(f"stale report: {args.output}", file=sys.stderr)
            return 1
        print(f"coverage-report-ok: {args.output}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote coverage report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
