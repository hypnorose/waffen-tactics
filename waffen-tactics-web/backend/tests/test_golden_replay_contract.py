import json
from pathlib import Path

from services.combat_event_reconstructor import CombatEventReconstructor


FIXTURE = Path(__file__).resolve().parents[1] / "test_fixtures" / "approved_replay_golden.json"


def test_shared_golden_fixture_reconstructs_to_its_authoritative_snapshot():
    with FIXTURE.open(encoding="utf-8") as handle:
        events = json.load(handle)

    initial = events[0]
    reconstructor = CombatEventReconstructor()
    reconstructor.initialize_from_snapshot({
        "player_units": initial["player_units"],
        "opponent_units": initial["opponent_units"],
    })

    for event in events[1:]:
        reconstructor.process_event(event["type"], event)

    snapshot = events[-1]

    def contract_view(unit):
        return {
            field: unit.get(field)
            for field in (
                "id", "name", "hp", "max_hp", "attack", "defense",
                "attack_speed", "star_level", "position", "effects",
                "current_mana", "max_mana", "shield", "buffed_stats",
            )
        }

    assert {
        unit_id: contract_view(unit)
        for unit_id, unit in reconstructor.reconstructed_player_units.items()
    } == {
        unit["id"]: contract_view(unit) for unit in snapshot["player_units"]
    }
    assert {
        unit_id: contract_view(unit)
        for unit_id, unit in reconstructor.reconstructed_opponent_units.items()
    } == {
        unit["id"]: contract_view(unit) for unit in snapshot["opponent_units"]
    }
