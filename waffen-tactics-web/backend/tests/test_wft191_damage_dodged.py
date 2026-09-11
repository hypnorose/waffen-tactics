from routes.game_combat import map_event_to_sse_payload
from services.combat_event_reconstructor import CombatEventReconstructor


def _snapshot():
    return {
        "player_units": [{"id": "player_1", "hp": 100, "shield": 0}],
        "opponent_units": [{"id": "opp_1", "hp": 100, "shield": 0}],
    }


def test_wft191_maps_production_damage_dodged_shape_at_seq_84():
    source = {
        "type": "damage_dodged",
        "unit_id": "opp_1",
        "unit_name": "Target",
        "attacker_id": "player_1",
        "side": "team_a",
        "timestamp": 8.4,
        "seq": 84,
        "event_id": "combat:84",
        "game_state": _snapshot(),
    }

    mapped = map_event_to_sse_payload("damage_dodged", source)

    assert mapped["type"] == "damage_dodged"
    assert mapped["type"] != "unit_attack"
    assert mapped["unit_id"] == "opp_1"
    assert mapped["unit_name"] == "Target"
    assert mapped["target_id"] == "opp_1"
    assert mapped["target_name"] == "Target"
    assert mapped["attacker_id"] == "player_1"
    assert mapped["damage"] == 0
    assert mapped["applied_damage"] == 0
    assert mapped["dodged"] is True
    assert mapped["side"] == "team_a"
    assert mapped["seq"] == 84
    assert mapped["event_id"] == "combat:84"
    assert mapped["game_state"] == source["game_state"]
    assert mapped["game_state"] is not source["game_state"]


def test_wft191_maps_canonical_noop_state_and_item_context():
    source = {
        "unit_id": "opp_1",
        "unit_name": "Target",
        "target_id": "opp_1",
        "target_name": "Target",
        "attacker_id": "player_1",
        "attacker_name": "Attacker",
        "attacker_current_mana": 40,
        "attacker_max_mana": 100,
        "pre_hp": 100,
        "post_hp": 100,
        "target_hp": 100,
        "unit_hp": 100,
        "unit_shield": 7,
        "post_shield": 7,
        "shield_absorbed": 0,
        "damage_type": "physical",
        "cause": "set2_dodge",
        "bonus_attack": False,
        "item_id": "item-1",
        "item_effect_id": "item-effect-1",
        "seq": 84,
        "timestamp": 8.4,
    }

    mapped = map_event_to_sse_payload("damage_dodged", source)

    assert mapped["attacker_name"] == "Attacker"
    assert mapped["attacker_current_mana"] == 40
    assert mapped["target_hp"] == 100
    assert mapped["post_hp"] == 100
    assert mapped["post_shield"] == 7
    assert mapped["cause"] == "set2_dodge"
    assert mapped["item_id"] == "item-1"
    assert mapped["item_effect_id"] == "item-effect-1"


def test_wft191_reconstructor_accepts_dodge_without_mutating_hp_or_shield():
    reconstructor = CombatEventReconstructor()
    snapshot = _snapshot()
    reconstructor.initialize_from_snapshot(snapshot)

    reconstructor.process_event(
        "damage_dodged",
        {
            "unit_id": "opp_1",
            "target_id": "opp_1",
            "attacker_id": "player_1",
            "damage": 0,
            "applied_damage": 0,
            "shield_absorbed": 0,
            "target_hp": 100,
            "post_hp": 100,
            "post_shield": 0,
            "seq": 84,
        },
    )

    assert reconstructor.reconstructed_opponent_units["opp_1"]["hp"] == 100
    assert reconstructor.reconstructed_opponent_units["opp_1"]["shield"] == 0

