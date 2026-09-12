import json

import pytest

from routes.game_combat import map_event_to_sse_payload
from services.combat_event_reconstructor import CombatEventReconstructor
from services.combat_snapshot_contract import (
    CombatSnapshotContractError,
    dumps_combat_snapshot,
    validate_combat_snapshot,
)


def _unit(unit_id: str, hp: int = 100):
    return {
        "id": unit_id,
        "name": unit_id,
        "hp": hp,
        "max_hp": 100,
        "current_mana": 40,
        "max_mana": 100,
        "shield": 7,
        "effects": [{
            "id": f"effect:{unit_id}",
            "type": "buff",
            "stat": "attack",
            "value": 2,
        }],
        "traits": ["frontline"],
        "buffed_stats": {"hp": 100, "attack": 12, "defense": 5},
        "item_runtime_state": {"item-1": {"stacks": 1}},
        "passive": None,
    }


def _snapshot():
    return {
        "player_units": [_unit("player-1")],
        "opponent_units": [_unit("opponent-1", hp=80)],
    }


def test_snapshot_round_trip_keeps_units_effects_and_arrays_structured():
    encoded = dumps_combat_snapshot(_snapshot(), context="wft203 test")
    round_tripped = json.loads(encoded)

    assert isinstance(round_tripped["player_units"][0], dict)
    assert isinstance(round_tripped["player_units"][0]["effects"], list)
    assert isinstance(round_tripped["player_units"][0]["effects"][0], dict)
    assert "@{" not in encoded
    assert "System.Object[]" not in encoded


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("player_units", "@{id=player-1}", "an array of unit objects"),
        ("opponent_units", "System.Object[]", "an array of unit objects"),
        ("player_units", ["@{id=player-1}"], "an object"),
    ],
)
def test_snapshot_rejects_stringified_units_and_arrays(field, value, expected):
    snapshot = _snapshot()
    snapshot[field] = value

    with pytest.raises(CombatSnapshotContractError, match=rf"field=.*{field}|field=.*player_units\[0\]"):
        validate_combat_snapshot(snapshot, context="state_snapshot seq=90")


def test_snapshot_rejects_malformed_effect_with_event_and_sequence_context():
    snapshot = _snapshot()
    snapshot["player_units"][0]["effects"] = ["System.Object[]"]

    with pytest.raises(CombatSnapshotContractError, match=r"state_snapshot seq=90.*effects\[0\]"):
        validate_combat_snapshot(snapshot, context="state_snapshot seq=90")


def test_sse_mapping_validates_embedded_snapshot_before_copying_it():
    snapshot = _snapshot()
    snapshot["opponent_units"] = "@{id=opponent-1}"

    with pytest.raises(CombatSnapshotContractError, match=r"unit_attack game_state seq=12.*opponent_units"):
        map_event_to_sse_payload(
            "unit_attack",
            {
                "attacker_id": "player-1",
                "target_id": "opponent-1",
                "target_hp": 80,
                "game_state": snapshot,
                "seq": 12,
            },
        )


def test_reconstructor_rejects_stringified_snapshot_without_fallback_parsing():
    snapshot = _snapshot()
    snapshot["player_units"] = "@{id=player-1}"

    with pytest.raises(CombatSnapshotContractError, match=r"snapshot seq=90.*player_units"):
        CombatEventReconstructor().initialize_from_snapshot({**snapshot, "seq": 90})
