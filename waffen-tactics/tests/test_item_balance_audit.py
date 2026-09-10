import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from item_balance_audit import audit_matrix, load_matrix  # noqa: E402


def test_item_balance_audit_reports_contract_and_runtime_boundary():
    report = audit_matrix(load_matrix())

    assert report["contract"]["status"] == "PASS"
    assert report["contract"]["base_count"] == 6
    assert report["contract"]["recipe_count"] == 21
    assert report["contract"]["a_plus_a_count"] == 6
    assert report["simulation"]["status"] == "insufficient-data"
    assert report["simulation"]["pairwise"]["runs"] == 0
    assert report["simulation"]["team"]["runs"] == 0


def test_item_balance_audit_flags_each_requested_contract_outlier_family():
    report = audit_matrix(load_matrix())
    flags = report["outlier_review"]["flag_counts"]

    assert flags["+600_hp"] == 1
    assert flags["+30_attack"] == 1
    assert flags["2pct_max_hp_per_second"] == 1
    assert flags["20_mana_per_second"] == 1
    assert flags["reflect"] == 1
    assert flags["lifesteal"] == 1
    assert flags["multi_target"] == 2
    assert flags["stack_cap_10"] == 1
    assert flags["stack_cap_30"] == 1


def test_item_balance_audit_keeps_author_decisions_pending():
    report = audit_matrix(load_matrix())

    assert all(row["stat_power"]["author_decision"] == "pending" for row in report["recipes"])
    assert all(row["effect_power"]["status"] == "insufficient-data" for row in report["recipes"])
