"""WFT-54 regression checks for the active Set 2 audit boundary."""

from tools.balance_audit import load_raw_data, roster_integrity
from waffen_tactics.services.data_loader import load_game_data


def test_balance_audit_uses_active_set2_contract_not_legacy_class_metadata():
    raw_units, raw_traits, raw_roles = load_raw_data()
    report = roster_integrity(
        raw_units,
        raw_traits,
        load_game_data().units,
        raw_roles["roles"],
    )

    assert report["unit_count"] == 32
    assert report["trait_count"] == 12
    assert report["active_set2_contract_issues"] == []
    assert report["missing_required_fields"] == []
    assert report["missing_faction_or_class"] == [
        {"unit_id": "skibidi_kubus", "missing": ["classes"]}
    ]
