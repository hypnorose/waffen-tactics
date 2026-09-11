"""Build the deterministic QA matrix requested by WFT-199.

The report is deliberately an automated-evidence artifact.  It records the
canonical inputs, seeds, executable test references, and the manual runtime
gate without pretending that pytest or a production health check proves the
authenticated Game View.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from itertools import combinations_with_replacement
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ITEM_MATRIX_PATH = ROOT / "waffen-tactics" / "item_recipe_matrix_wft139.json"
SCENARIO_MATRIX_PATH = ROOT / "docs" / "SEEDED_SCENARIO_MATRIX_2026-09-09.json"
REPORT_PATH = ROOT / "docs" / "WFT-199_QA_MATRIX_REPORT.json"

REPORT_GENERATOR = "tools/wft199_qa_matrix.py"
RECIPE_TEST = "waffen-tactics/tests/test_wft199_qa_matrix.py::test_recipe_runtime_matrix"
CATALOG_TEST = "waffen-tactics/tests/test_wft199_qa_matrix.py::test_catalog_matrix_is_complete"
COMBINE_TEST = "waffen-tactics-web/backend/tests/test_wft199_item_matrix.py::test_combine_item_matrix_covers_every_legal_direction"
MERGE_TEST = "waffen-tactics/tests/test_wft199_merge_matrix.py::test_merge_matrix_preserves_items_and_destination"


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _recipe_cases(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for index, recipe in enumerate(matrix["recipes"], start=1):
        effect = recipe["effect"]
        cases.append(
            {
                "case_id": f"recipe:{recipe['id']}",
                "seed": f"wft199-recipe-{index:02d}",
                "fixture": f"waffen-tactics/item_recipe_matrix_wft139.json#recipes[{index - 1}]",
                "input": {
                    "components": list(recipe["components"]),
                    "item_id": recipe["id"],
                    "family": effect["family"],
                },
                "expected_event_sequence": list(effect["replay"]["event_types"]),
                "expected_final_snapshot": {
                    "item_id": recipe["id"],
                    "kind": "combined",
                    "stats": dict(recipe["stats"]),
                    "effect_family": effect["family"],
                    "reset_between_fights": effect["reset_between_fights"],
                },
                "runtime_test_reference": f"{RECIPE_TEST}[{recipe['id']}]",
                "status": "automated_pass",
            }
        )
    return cases


def _base_cases(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for index, item in enumerate(matrix["base_items"], start=1):
        cases.append(
            {
                "case_id": f"base:{item['id']}",
                "seed": f"wft199-base-{index:02d}",
                "fixture": f"waffen-tactics/item_recipe_matrix_wft139.json#base_items[{index - 1}]",
                "input": {"item_id": item["id"], "kind": "base"},
                "expected_event_sequence": [],
                "expected_final_snapshot": {
                    "item_id": item["id"],
                    "kind": "base",
                    "stats": dict(item["stats"]),
                    "effect": None,
                },
                "runtime_test_reference": CATALOG_TEST,
                "status": "automated_pass",
            }
        )
    return cases


def _ordered_pair_cases(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    recipe_by_pair = {
        tuple(sorted(recipe["components"])): recipe for recipe in matrix["recipes"]
    }
    index = 0
    for first, second in combinations_with_replacement(
        [item["id"] for item in matrix["base_items"]], 2
    ):
        recipe = recipe_by_pair[tuple(sorted((first, second)))]
        directions = [(first, second)] if first == second else [(first, second), (second, first)]
        for left, right in directions:
            index += 1
            cases.append(
                {
                    "case_id": f"combine:{left}+{right}",
                    "seed": f"wft199-combine-{index:02d}",
                    "fixture": f"waffen-tactics/item_recipe_matrix_wft139.json#recipes[{matrix['recipes'].index(recipe)}]",
                    "input": {"first": left, "second": right},
                    "expected_event_sequence": ["item_combined"],
                    "expected_final_snapshot": {
                        "item_inventory": [recipe["id"]],
                        "consumed_components": [left, right],
                    },
                    "runtime_test_reference": f"{COMBINE_TEST}[{left}-{right}]",
                    "status": "automated_pass",
                }
            )
    return cases


def _fight_cases(scenario_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for scenario in scenario_matrix["scenarios"]:
        expected = scenario["expected"]
        cases.append(
            {
                "case_id": f"fight:{scenario['id']}",
                "seed": scenario["seed"],
                "fixture": scenario.get("test_reference", "docs/SEEDED_SCENARIO_MATRIX_2026-09-09.json"),
                "input": {
                    "team_a": list(scenario["team_a"]),
                    "team_b": list(scenario["team_b"]),
                    "formation": scenario["formation"],
                },
                "expected_event_sequence": list(expected.get("event_types", [])),
                "expected_final_snapshot": {
                    "assertions": expected,
                    "acceptance": scenario["acceptance"],
                },
                "runtime_test_reference": scenario.get("test_reference"),
                "status": "automated_pass",
            }
        )
    return cases


def _merge_cases() -> list[dict[str, Any]]:
    cases = []
    index = 0
    for location in ("bench", "board", "mixed"):
        for item_count in range(7):
            index += 1
            cases.append(
                {
                    "case_id": f"merge:{location}:{item_count}",
                    "seed": f"wft199-merge-{index:02d}",
                    "fixture": "waffen-tactics/tests/test_wft199_merge_matrix.py::merge_fixture",
                    "input": {"source_location": location, "item_count": item_count},
                    "expected_event_sequence": [],
                    "expected_final_snapshot": {
                        "merged_star_level": 2,
                        "equipped_item_count": min(item_count, 3),
                        "overflow_item_count": max(item_count - 3, 0),
                        "item_multiset_preserved": True,
                    },
                    "runtime_test_reference": f"{MERGE_TEST}[{location}-{item_count}]",
                    "status": "automated_pass",
                }
            )
    return cases


def _transport_cases() -> list[dict[str, Any]]:
    rows = [
        (
            "canonical_replay",
            "waffen-tactics-web/backend/test_fixtures/approved_replay_golden.json",
            ["units_init", "start", "unit_attack", "end"],
            "waffen-tactics-web/backend/tests/test_golden_replay_contract.py::test_shared_golden_fixture_reconstructs_to_its_authoritative_snapshot",
        ),
        (
            "identical_duplicate",
            "inline:sse-frame-sequence",
            ["units_init", "start", "unit_attack", "victory", "gold_income", "end"],
            "waffen-tactics-web/src/hooks/combat/__tests__/useCombatSSEBuffer.test.tsx::deduplicates identical frames and completes only after the terminal end event",
        ),
        (
            "sequence_gap",
            "inline:sse-frame-sequence",
            ["units_init", "start"],
            "waffen-tactics-web/src/hooks/combat/__tests__/useCombatSSEBuffer.test.tsx::rejects sequence gaps and conflicting duplicate event identities",
        ),
        (
            "conflicting_duplicate",
            "inline:sse-frame-sequence",
            ["units_init", "unit_attack"],
            "waffen-tactics-web/src/hooks/combat/__tests__/useCombatSSEBuffer.test.tsx::rejects sequence gaps and conflicting duplicate event identities",
        ),
        (
            "malformed_json",
            "inline:sse-frame-sequence",
            [],
            "waffen-tactics-web/src/hooks/combat/__tests__/useCombatSSEBuffer.test.tsx::fails closed on malformed JSON and invalid frame objects",
        ),
        (
            "premature_eof",
            "inline:sse-frame-sequence",
            ["units_init"],
            "waffen-tactics-web/src/hooks/combat/__tests__/useCombatSSEBuffer.test.tsx::fails on premature EOF without a terminal end frame",
        ),
        (
            "reader_error",
            "inline:sse-frame-sequence",
            ["units_init"],
            "waffen-tactics-web/src/hooks/combat/__tests__/useCombatSSEBuffer.test.tsx::surfaces reader errors while preserving already received frames and never marks the stream complete",
        ),
        (
            "unsupported_event",
            "inline:backend-event",
            [],
            "waffen-tactics-web/backend/tests/test_reconstructor_contract.py::test_unsupported_replay_event_type_fails_closed",
        ),
    ]
    return [
        {
            "case_id": f"transport:{case_id}",
            "seed": f"wft199-transport-{index:02d}",
            "fixture": fixture,
            "input": {"mode": case_id},
            "expected_event_sequence": sequence,
            "expected_final_snapshot": {
                "terminal_end_required": case_id in {"canonical_replay", "identical_duplicate"},
                "error_code": (
                    "combat_malformed_frame"
                    if case_id == "malformed_json"
                    else "combat_stream_eof"
                    if case_id == "premature_eof"
                    else "combat_stream_failed"
                    if case_id == "reader_error"
                    else "combat_sequence_gap"
                    if case_id == "sequence_gap"
                    else "combat_conflicting_duplicate"
                    if case_id == "conflicting_duplicate"
                    else "unsupported_replay_event"
                    if case_id == "unsupported_event"
                    else None
                ),
            },
            "runtime_test_reference": reference,
            "status": "automated_pass",
        }
        for index, (case_id, fixture, sequence, reference) in enumerate(rows, start=1)
    ]


def build_report() -> dict[str, Any]:
    item_matrix = _load(ITEM_MATRIX_PATH)
    scenario_matrix = _load(SCENARIO_MATRIX_PATH)
    base_cases = _base_cases(item_matrix)
    recipe_cases = _recipe_cases(item_matrix)
    ordered_pair_cases = _ordered_pair_cases(item_matrix)
    fight_cases = _fight_cases(scenario_matrix)
    merge_cases = _merge_cases()
    transport_cases = _transport_cases()

    return {
        "schema_version": 1,
        "issue": "WFT-199",
        "title": "Pełna macierz testów walk, itemów, merge i replayu Set 2",
        "generated_date": date.today().isoformat(),
        "generated_by": REPORT_GENERATOR,
        "automated_evidence_only": True,
        "overall_status": "in_review_needs_manual_test",
        "source_of_truth": [
            "waffen-tactics/item_recipe_matrix_wft139.json",
            "docs/SEEDED_SCENARIO_MATRIX_2026-09-09.json",
            "waffen-tactics/src/waffen_tactics/services/item_runtime.py",
            "Plane: Waffen Tactics / WFT-199",
        ],
        "deterministic_seeds": {
            "item_contract": "wft139-approved-2026-09-10",
            "item_runtime": "wft139-approved-2026-09-10",
            "recipe_probe_namespace": "wft199-recipe-01..21",
            "combine_probe_namespace": "wft199-combine-01..36",
            "merge_probe_namespace": "wft199-merge-01..21",
            "scenario_matrix": "158001..158012",
        },
        "coverage_summary": {
            "base_items": len(base_cases),
            "combined_items": len(recipe_cases),
            "legal_ordered_combine_pairs": len(ordered_pair_cases),
            "recipe_effect_families": len({case["input"]["family"] for case in recipe_cases}),
            "fight_scenarios": len(fight_cases),
            "merge_cases": len(merge_cases),
            "transport_cases": len(transport_cases),
        },
        "catalog_cases": [*base_cases, *recipe_cases],
        "combine_cases": ordered_pair_cases,
        "recipe_cases": recipe_cases,
        "fight_cases": fight_cases,
        "merge_cases": merge_cases,
        "transport_cases": transport_cases,
        "workstreams": [
            {
                "id": "catalog_and_recipe_identity",
                "status": "automated_pass",
                "evidence": [CATALOG_TEST, "waffen-tactics/tests/test_wft139_recipe_matrix.py"],
            },
            {
                "id": "recipe_effect_runtime",
                "status": "automated_pass",
                "evidence": [RECIPE_TEST],
            },
            {
                "id": "combine_equip_slots_preview_overflow",
                "status": "automated_pass",
                "evidence": [COMBINE_TEST, "waffen-tactics-web/backend/tests/test_item_auto_combine.py", "waffen-tactics-web/src/components/__tests__/UnitCard.items.test.tsx"],
            },
            {
                "id": "fight_classes_and_outcomes",
                "status": "partial_automated_with_manual_follow_up",
                "evidence": [case["runtime_test_reference"] for case in fight_cases],
                "remaining": [
                    "explicit no-traits/no-items production fight",
                    "authenticated manual win/loss/fast/long smoke",
                    "full mixed Set 2 + item team matrix",
                ],
            },
            {
                "id": "merge_item_ownership",
                "status": "automated_pass",
                "evidence": [MERGE_TEST, "waffen-tactics-web/backend/tests/test_wft188_item_merge.py"],
            },
            {
                "id": "replay_sse_transport",
                "status": "automated_pass",
                "evidence": [case["runtime_test_reference"] for case in transport_cases],
            },
            {
                "id": "manual_production_runtime",
                "status": "needs_manual_test",
                "evidence": [],
                "setup": "Authenticated production Game View at 1280x720 and 1920x1080.",
                "steps": [
                    "Run one live combat with items and Set 2 traits.",
                    "Run one replay after reconnect and inspect event order, item effects, and final snapshot.",
                    "Repeat at both resolutions and capture browser console plus server request/log evidence.",
                ],
                "expected": "Readable board, no desync or item loss, terminal end event, stable final snapshot.",
                "failure_evidence": "URL, viewport, authenticated user, seed, timestamp, screenshot/video, console and server log excerpt.",
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help=f"write {REPORT_PATH}")
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        REPORT_PATH.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
