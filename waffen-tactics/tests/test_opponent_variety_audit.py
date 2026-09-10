from types import SimpleNamespace

from tools.balance_audit import (
    _classify_opponent_behavior,
    opponent_variety_audit,
)
from waffen_tactics.services.data_loader import load_game_data


def _unit(role="fighter", passive=None):
    return SimpleNamespace(role=role, passive=passive or {})


def test_classification_distinguishes_intended_observation_categories():
    assert _classify_opponent_behavior(
        unit=_unit(), attacks=[{"is_skill": False}, {"is_skill": False}], skill_casts=[],
        final_hp=10, timeout=True, opponent_team_alive=True,
    )[0] == "repeated_basic_attack"
    assert _classify_opponent_behavior(
        unit=_unit(), attacks=[{"is_skill": False}], skill_casts=[{}],
        final_hp=10, timeout=False, opponent_team_alive=True,
    )[0] == "targeted_action"
    assert _classify_opponent_behavior(
        unit=_unit(), attacks=[], skill_casts=[], final_hp=0,
        timeout=False, opponent_team_alive=True,
    )[0] == "combat_ended_before_action"
    assert _classify_opponent_behavior(
        unit=_unit(role="defender", passive={"kind": "threshold"}), attacks=[], skill_casts=[],
        final_hp=10, timeout=True, opponent_team_alive=True,
    )[0] == "intentional_defensive_identity"
    assert _classify_opponent_behavior(
        unit=_unit(), attacks=[], skill_casts=[], final_hp=10,
        timeout=False, opponent_team_alive=False,
    )[0] == "no_legal_action"
    assert _classify_opponent_behavior(
        unit=_unit(), attacks=[], skill_casts=[], final_hp=10,
        timeout=False, opponent_team_alive=True,
    )[0] == "runtime_defect_candidate"


def test_opponent_variety_audit_is_seeded_and_captures_required_dimensions():
    units = load_game_data().units
    first = opponent_variety_audit(units, matches=2, team_size=2, seed_base=42000)
    second = opponent_variety_audit(units, matches=2, team_size=2, seed_base=42000)

    assert first["summary"] == second["summary"]
    assert first["opponent_rows"] == second["opponent_rows"]
    assert first["summary"]["battle_errors"] == 0
    assert first["summary"]["opponents_observed"] == 4
    assert first["metadata"]["read_only_audit"] is True
    assert first["metadata"]["position_contract"]
    assert first["metadata"]["production_position_note"]
    assert first["metadata"]["skill_contract_note"]

    row = first["opponent_rows"][0]
    assert {"movement", "target_positions", "action_types", "passive_effects", "resource_usage", "damage_dealt"} <= row.keys()
    assert "behavior_signature" in row
    assert row["movement"]["position_trace"]
    assert row["resource_usage"]["mana_direction"]
