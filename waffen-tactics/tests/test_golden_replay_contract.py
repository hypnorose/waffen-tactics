import json
from pathlib import Path


FIXTURE = Path(__file__).resolve().parents[2] / "waffen-tactics-web" / "backend" / "test_fixtures" / "approved_replay_golden.json"


def load_golden_events():
    with FIXTURE.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_golden_replay_has_ordered_authoritative_events_and_snapshot():
    events = load_golden_events()
    assert [event["seq"] for event in events] == list(range(1, len(events) + 1))

    attacks = [event for event in events if event["type"] == "unit_attack"]
    assert [(event["attacker_id"], event["target_id"]) for event in attacks] == [
        ("p_front", "opp_front"),
        ("p_back", "opp_back"),
    ]
    assert all("target_hp" in event for event in attacks)

    passive_events = [event for event in events if event["type"] == "passive_triggered"]
    assert passive_events
    assert all(event["source_id"].startswith("passive:") for event in passive_events)

    snapshots = [event for event in events if event["type"] == "state_snapshot"]
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert next(unit for unit in snapshot["opponent_units"] if unit["id"] == "opp_front")["hp"] == 0
    assert next(unit for unit in snapshot["opponent_units"] if unit["id"] == "opp_back")["hp"] == 80
