"""WFT-198 canonical combat event contract checks."""

from __future__ import annotations

import copy

import pytest

from tools.verify_combat_event_contract import _load_contract, verify_contract


def test_combat_event_contract_covers_all_layers_and_invariants():
    result = verify_contract()

    assert result["contract_id"] == "WFT-198"
    assert result["event_count"] == 30
    assert result["control_event_count"] == 6
    assert result["status"] == "pass"


def test_contract_fails_closed_when_a_new_event_has_no_layer_mapping():
    contract = copy.deepcopy(_load_contract())
    contract["events"].append({
        "type": "future_combat_event",
        "origin": "core",
        "mapper": "map_branch",
        "reconstructor": "explicit_noop",
        "frontend": "case",
        "required_fields": ["type", "seq", "event_id"],
        "post_state": "none",
        "ordering": "strict_seq",
        "dedupe": "event_id",
        "presentation": "combat_log",
    })

    with pytest.raises(AssertionError, match="future_combat_event: (core origin|SSE mapper|backend reconstructor|frontend reducer)"):
        verify_contract(contract)


def test_non_control_contract_entries_require_event_identity():
    contract = copy.deepcopy(_load_contract())
    contract["events"][6]["required_fields"].remove("event_id")

    with pytest.raises(AssertionError, match="state_snapshot: non-control frame must require event_id"):
        verify_contract(contract)
