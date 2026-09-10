import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.seeded_coverage_report import REPORT_PATH, build_report  # noqa: E402


def test_seeded_coverage_report_is_current_and_separates_manual_runtime_evidence():
    with REPORT_PATH.open(encoding="utf-8") as handle:
        checked_in_report = json.load(handle)

    assert checked_in_report == build_report()
    assert checked_in_report["automated_evidence_only"] is True
    assert set(checked_in_report["failure_domains"]) == {
        "data", "runtime", "emitter", "reconstructor", "ui"
    }
    assert all(
        domain["status"] == "automated_contract"
        for domain in checked_in_report["failure_domains"].values()
    )
    assert checked_in_report["coverage"]["unit"]["uncovered_ids"] == []
    assert checked_in_report["coverage"]["unit"]["passive_ids_without_unit"] == []
    assert checked_in_report["coverage"]["trait"]["boundary_states"] == ["below", "exact", "next"]
    assert checked_in_report["coverage"]["trigger_family"]["positive_and_negative_paths"] is True
    assert checked_in_report["coverage"]["cross_layer_replay"]["missing_event_fails"] is True
    assert checked_in_report["manual_runtime"]["status"] == "pending"
