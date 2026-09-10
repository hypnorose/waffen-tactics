"""Audit the approved WFT-139 item matrix without inventing balance decisions.

The report deliberately separates evidence available from the authored matrix
from combat measurements.  Until the item runtime gates are complete, dynamic
effect power is reported as ``insufficient-data`` rather than inferred from
descriptions or from a stat-only simulator.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "waffen-tactics" / "item_recipe_matrix_wft139.json"
DEFAULT_DATE = "2026-09-11"
CONTENT_SEED = "wft139-approved-2026-09-10"


def load_matrix(path: Path = MATRIX_PATH) -> dict[str, Any]:
    matrix = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(matrix, dict):
        raise ValueError("WFT-139 matrix must be a JSON object")
    return matrix


def validate_contract(matrix: dict[str, Any]) -> dict[str, Any]:
    source_root = ROOT / "waffen-tactics" / "src"
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))
    from waffen_tactics.services.item_contract import ItemContractError, validate_item_matrix

    records = [*matrix.get("base_items", []), *matrix.get("recipes", [])]
    try:
        validate_item_matrix(records)
    except ItemContractError as exc:
        return {"status": "FAIL", "errors": list(exc.errors)}
    return {"status": "PASS", "errors": []}


def _static_flags(recipe: dict[str, Any]) -> list[str]:
    stats = recipe.get("stats") or {}
    effect = recipe.get("effect") or {}
    parameters = effect.get("parameters") or {}
    flags: list[str] = []

    if stats.get("hp", 0) >= 600:
        flags.append("+600_hp")
    if stats.get("attack", 0) >= 30:
        flags.append("+30_attack")
    if parameters.get("heal_owner_max_hp_ratio_per_second", 0) >= 0.02:
        flags.append("2pct_max_hp_per_second")
    if parameters.get("mana_per_second", 0) >= 20:
        flags.append("20_mana_per_second")
    if effect.get("family") == "reflect":
        flags.append("reflect")
    if stats.get("lifesteal_percent", 0) > 0 or effect.get("family") == "lifesteal":
        flags.append("lifesteal")
    if (
        "multi_target" in str(effect.get("family", ""))
        or "additional_target_count" in parameters
        or "target_count" in parameters
    ):
        flags.append("multi_target")

    max_stacks = (effect.get("stacking") or {}).get("max_stacks")
    if isinstance(max_stacks, int) and max_stacks > 1:
        flags.append(f"stack_cap_{max_stacks}")
    return flags


def audit_matrix(matrix: dict[str, Any], generated_date: str = DEFAULT_DATE) -> dict[str, Any]:
    bases = matrix.get("base_items") or []
    recipes = matrix.get("recipes") or []
    contract = validate_contract(matrix)
    recipe_rows = []
    flag_counts: Counter[str] = Counter()

    for recipe in recipes:
        flags = _static_flags(recipe)
        flag_counts.update(flags)
        recipe_rows.append(
            {
                "item_id": recipe.get("id"),
                "name": recipe.get("name"),
                "components": recipe.get("components"),
                "stats": recipe.get("stats"),
                "effect_family": (recipe.get("effect") or {}).get("family"),
                "static_outlier_flags": flags,
                "stat_power": {
                    "status": "contract-review",
                    "evidence": "explicit WFT-139 stats",
                    "author_decision": "pending",
                },
                "effect_power": {
                    "status": "insufficient-data",
                    "evidence": "item combat runtime gates WFT-142..145 are not complete",
                    "author_decision": "pending",
                },
            }
        )

    return {
        "report": "WFT-150 item balance audit",
        "generated_date": generated_date,
        "content_source": "WFT-139",
        "content_version": matrix.get("content_version"),
        "content_seed": matrix.get("deterministic_seed", CONTENT_SEED),
        "contract": {
            **contract,
            "base_count": len(bases),
            "recipe_count": len(recipes),
            "expected_pairs": 21,
            "a_plus_a_count": sum(
                1 for recipe in recipes if recipe.get("components", [None])[0] == recipe.get("components", [None, None])[1]
            ),
        },
        "simulation": {
            "status": "insufficient-data",
            "reason": "Dynamic item effects are not yet executed by the canonical combat runtime; stat-only simulations would misrepresent effect power.",
            "pairwise": {
                "status": "not-run",
                "runs": 0,
                "combat_seeds": [],
                "configuration": ["without_item", "base_item", "combined_item"],
            },
            "team": {
                "status": "not-run",
                "runs": 0,
                "combat_seeds": [],
                "team_sizes": [5, 10],
            },
            "confidence": None,
        },
        "outlier_review": {
            "status": "contract-review-only",
            "decision_policy": "No automatic nerf/buff; every flagged item requires author decision after runtime measurements.",
            "flag_counts": dict(sorted(flag_counts.items())),
        },
        "recipes": recipe_rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Waffen Tactics — WFT-150 Item Balance Audit",
        "",
        f"- Generated: `{report['generated_date']}`",
        f"- Content source: `{report['content_source']}` / `{report['content_version']}`",
        f"- Content seed: `{report['content_seed']}`",
        "- Runtime measurement: **INSUFFICIENT-DATA** — item effects are not yet executed by the canonical combat runtime.",
        "",
        "## Contract evidence",
        "",
        f"- Contract validation: **{report['contract']['status']}**",
        f"- Bases: `{report['contract']['base_count']}`; recipes: `{report['contract']['recipe_count']}`; A+A recipes: `{report['contract']['a_plus_a_count']}`.",
        "- No authored stat or effect value was changed by this audit.",
        "",
        "## Simulation gate",
        "",
        "Pairwise and team simulations were not run because a stat-only run would omit the approved dynamic effects and produce misleading balance evidence.",
        "",
        "| Item | Static flags | Stat review | Effect review | Author decision |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["recipes"]:
        flags = ", ".join(row["static_outlier_flags"]) or "—"
        lines.append(
            f"| {row['item_id']} | {flags} | {row['stat_power']['status']} | {row['effect_power']['status']} | pending |"
        )
    lines.extend(
        [
            "",
            "## Next gate",
            "",
            "After WFT-142, WFT-143, WFT-144 and WFT-145 expose deterministic item execution through the shared combat path, rerun this audit with real combat seeds, pairwise/team counts, confidence markers and expected-vs-actual scenarios.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated-date", default=DEFAULT_DATE)
    parser.add_argument("--output-json", type=Path, default=ROOT / "docs" / "ITEM_BALANCE_AUDIT_2026-09-11.json")
    parser.add_argument("--output-md", type=Path, default=ROOT / "docs" / "ITEM_BALANCE_AUDIT_2026-09-11.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = audit_matrix(load_matrix(), args.generated_date)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"json": str(args.output_json), "markdown": str(args.output_md), "status": report["contract"]["status"]}))


if __name__ == "__main__":
    main()
