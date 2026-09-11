"""Regression coverage for WFT-187 formation transitions in combat replay."""

import json
from pathlib import Path

import pytest

from services.combat_event_reconstructor import CombatEventReconstructor
import routes.game_combat as game_combat


FIXTURE_DIR = Path(__file__).parents[1] / "test_fixtures"
FIXTURES = [
    FIXTURE_DIR / "wft187_desync_1789119468361.json",
    FIXTURE_DIR / "wft187_desync_1789119699080.json",
]


def _unit(unit_id, position="front"):
    return {
        "id": unit_id,
        "name": unit_id,
        "hp": 100,
        "max_hp": 100,
        "current_mana": 0,
        "max_mana": 100,
        "attack": 10,
        "defense": 5,
        "attack_speed": 1.0,
        "position": position,
        "shield": 0,
        "effects": [],
    }


@pytest.mark.parametrize("fixture_path", FIXTURES, ids=lambda path: path.stem)
def test_supplied_desync_fixture_replays_position_before_following_attack(fixture_path):
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    desync = fixture["desync"]
    legacy_passives = [
        event for event in fixture["legacy_window"][:-1]
        if event["type"] == "passive_triggered" and event.get("effect") == "swap_enemy_line"
    ]
    following_attack = fixture["legacy_window"][-1]

    initial_opponent = [_unit(desync["unit_id"], desync["ui_position"]), _unit("opp_0"), _unit("opp_2")]
    reconstructor = CombatEventReconstructor()
    reconstructor.initialize_from_snapshot({
        "player_units": [_unit("e7e66be4")],
        "opponent_units": initial_opponent,
    })

    formation_events = []
    for legacy_passive in legacy_passives:
        target_id = legacy_passive["target_id"]
        current_position = reconstructor.reconstructed_opponent_units[target_id]["position"]
        new_position = "back" if current_position == "front" else "front"
        formation = {
            "type": "formation_changed",
            "seq": legacy_passive["seq"],
            "event_id": f"fixture:{fixture['source_export']}:formation:{target_id}",
            "unit_id": target_id,
            "unit_name": "Anamol04" if target_id == desync["unit_id"] else target_id,
            "previous_position": current_position,
            "new_position": new_position,
            "position": new_position,
            "source_id": legacy_passive["unit_id"],
            "passive_id": legacy_passive["unit_id"],
            "trigger": "on_bonus_attack",
            "effect": legacy_passive["effect"],
            "cause": legacy_passive["effect"],
            "side": "team_a",
            "target_side": "team_b",
            "timestamp": 3.75,
        }
        reconstructor.process_event("formation_changed", formation)
        formation_events.append(formation)

    assert reconstructor.reconstructed_opponent_units[desync["unit_id"]]["position"] == desync["server_position"]
    assert len(formation_events) == len(legacy_passives)
    assert all(event["seq"] < following_attack["seq"] for event in formation_events)
    for legacy_passive in legacy_passives:
        assert reconstructor.reconstructed_opponent_units[legacy_passive["target_id"]]["position"] == "back"

    # The same committed event can be observed twice after reconnect; it must
    # remain a no-op instead of toggling the unit back to the front line.
    for formation in formation_events:
        reconstructor.process_event("formation_changed", formation)
    assert reconstructor.reconstructed_opponent_units[desync["unit_id"]]["position"] == desync["server_position"]

    assert following_attack["seq"] > formation["seq"]


def test_formation_event_sse_mapping_preserves_transition_and_transport_identity():
    payload = game_combat.map_event_to_sse_payload("formation_changed", {
        "unit_id": "opp_1",
        "unit_name": "Anamol04",
        "previous_position": "front",
        "new_position": "back",
        "source_id": "e7e66be4",
        "source_name": "Yossarian",
        "passive_id": "set2.passive.yossarian",
        "trigger": "on_bonus_attack",
        "effect": "swap_enemy_line",
        "cause": "swap_enemy_line",
        "side": "team_a",
        "target_side": "team_b",
        "timestamp": 3.75,
        "seq": 233,
        "event_id": "combat:233",
    })

    assert payload == {
        "type": "formation_changed",
        "unit_id": "opp_1",
        "unit_name": "Anamol04",
        "previous_position": "front",
        "new_position": "back",
        "position": "back",
        "source_id": "e7e66be4",
        "source_name": "Yossarian",
        "passive_id": "set2.passive.yossarian",
        "trigger": "on_bonus_attack",
        "effect": "swap_enemy_line",
        "cause": "swap_enemy_line",
        "side": "team_a",
        "target_side": "team_b",
        "timestamp": 3.75,
        "seq": 233,
        "event_id": "combat:233",
    }


def test_reconstructor_rejects_unknown_current_position_without_mutating_state():
    reconstructor = CombatEventReconstructor()
    reconstructor.initialize_from_snapshot({
        "player_units": [_unit("player")],
        "opponent_units": [_unit("opp_1", position=None)],
    })

    with pytest.raises(ValueError, match="position mismatch"):
        reconstructor.process_event("formation_changed", {
            "unit_id": "opp_1",
            "previous_position": "front",
            "new_position": "back",
            "event_id": "combat:unknown-current",
            "seq": 10,
        })

    assert reconstructor.reconstructed_opponent_units["opp_1"]["position"] is None


def test_formation_sse_mapping_requires_canonical_transport_identity():
    payload = {
        "unit_id": "opp_1",
        "previous_position": "front",
        "new_position": "back",
        "seq": 233,
    }

    with pytest.raises(RuntimeError, match="canonical event_id"):
        game_combat.map_event_to_sse_payload("formation_changed", payload)
