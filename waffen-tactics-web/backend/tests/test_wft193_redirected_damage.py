"""WFT-193 SSE and replay coverage for redirected damage."""

import copy

import pytest

from routes.game_combat import map_event_to_sse_payload
from services.combat_event_reconstructor import CombatEventReconstructor


def _snapshot():
    return {
        "player_units": [
            {"id": "attacker", "name": "Attacker", "hp": 100, "shield": 0, "effects": []},
        ],
        "opponent_units": [
            {"id": "redirected", "name": "Redirected", "hp": 8, "shield": 0, "effects": []},
        ],
    }


def _event():
    return {
        "type": "damage",
        "attacker_id": "attacker",
        "attacker_name": "Attacker",
        "target_id": "redirected",
        "target_name": "Redirected",
        "unit_id": "redirected",
        "unit_name": "Redirected",
        "pre_hp": 8,
        "post_hp": 0,
        "target_hp": 0,
        "unit_hp": 0,
        "damage": 20,
        "applied_damage": 20,
        "shield_absorbed": 0,
        "post_shield": 0,
        "unit_shield": 0,
        "cause": "set2_haxball_redirect",
        "side": "team_a",
        "timestamp": 1.2,
        "seq": 7,
        "event_id": "combat:7",
        "game_state": {
            "player_units": _snapshot()["player_units"],
            "opponent_units": [{"id": "redirected", "name": "Redirected", "hp": 0, "shield": 0, "effects": []}],
        },
    }


def test_damage_mapping_preserves_distinct_type_and_authoritative_fields():
    mapped = map_event_to_sse_payload("damage", _event())

    assert mapped["type"] == "damage"
    assert mapped["event_id"] == "combat:7"
    assert mapped["attacker_id"] == "attacker"
    assert mapped["target_id"] == "redirected"
    assert mapped["damage"] == mapped["applied_damage"] == 20
    assert mapped["pre_hp"] == 8
    assert mapped["post_hp"] == mapped["target_hp"] == 0
    assert mapped["post_shield"] == 0
    assert mapped["cause"] == "set2_haxball_redirect"
    assert mapped["game_state"]["opponent_units"][0]["hp"] == 0


@pytest.mark.parametrize("field", ["attacker_id", "target_id", "post_hp", "post_shield", "cause"])
def test_damage_mapping_fails_closed_when_canonical_field_is_missing(field):
    payload = copy.deepcopy(_event())
    payload[field] = None

    with pytest.raises(RuntimeError, match="damage missing required canonical fields"):
        map_event_to_sse_payload("damage", payload)


def test_damage_replay_applies_post_state_before_ordered_unit_death():
    mapped = map_event_to_sse_payload("damage", _event())
    reconstructor = CombatEventReconstructor()
    reconstructor.initialize_from_snapshot(_snapshot())

    reconstructor.process_event("damage", mapped)
    assert reconstructor.reconstructed_opponent_units["redirected"]["hp"] == 0
    assert reconstructor.reconstructed_opponent_units["redirected"]["shield"] == 0

    reconstructor.process_event("unit_died", {
        "type": "unit_died",
        "unit_id": "redirected",
        "unit_name": "Redirected",
        "post_hp": 0,
        "unit_hp": 0,
        "seq": 8,
        "event_id": "combat:8",
    })
    assert reconstructor.reconstructed_opponent_units["redirected"]["hp"] == 0
