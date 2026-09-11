"""WFT-198 transport/replay boundary checks."""

from __future__ import annotations

import copy

import pytest

from routes.game_combat import combat_error_sse_payload, map_event_to_sse_payload
from services.combat_event_reconstructor import CombatEventReconstructor


def _unit(unit_id: str):
    return {
        "id": unit_id,
        "hp": 100,
        "max_hp": 100,
        "current_mana": 0,
        "max_mana": 100,
        "attack": 10,
        "defense": 5,
        "attack_speed": 1.0,
        "shield": 0,
        "effects": [],
    }


def _reconstructor() -> CombatEventReconstructor:
    reconstructor = CombatEventReconstructor()
    reconstructor.initialize_from_snapshot({
        "player_units": [_unit("player")],
        "opponent_units": [_unit("opponent")],
    })
    return reconstructor


@pytest.mark.parametrize("event_type", ["start", "victory", "defeat", "gold_income", "end"])
def test_control_frames_are_explicit_replay_noops(event_type: str):
    reconstructor = _reconstructor()
    before = copy.deepcopy(reconstructor.reconstructed_player_units)

    reconstructor.process_event(event_type, {"type": event_type, "seq": 0})

    assert reconstructor.reconstructed_player_units == before


def test_units_init_is_explicit_noop_after_replay_snapshot():
    reconstructor = _reconstructor()
    before = copy.deepcopy(reconstructor.reconstructed_opponent_units)

    reconstructor.process_event("units_init", {
        "type": "units_init",
        "seq": 0,
        "player_units": [_unit("player")],
        "opponent_units": [_unit("opponent")],
    })

    assert reconstructor.reconstructed_opponent_units == before


def test_unit_died_transport_contains_authoritative_post_hp():
    payload = map_event_to_sse_payload("unit_died", {
        "unit_id": "player",
        "unit_name": "Player",
        "seq": 1,
        "event_id": "combat:1",
    })

    assert payload["type"] == "unit_died"
    assert payload["post_hp"] == 0
    assert payload["unit_hp"] == 0
    assert payload["event_id"] == "combat:1"


def test_transport_error_payload_has_the_canonical_error_shape():
    class Error:
        code = "combat_stream_failed"
        retriable = True
        safe_message = "Combat failed."

    assert combat_error_sse_payload(Error()) == {
        "type": "error",
        "code": "combat_stream_failed",
        "message": "Combat failed.",
        "retriable": True,
    }
