import copy
import json
from pathlib import Path

import pytest

from routes.game_combat import map_event_to_sse_payload
from services.combat_event_reconstructor import CombatEventReconstructor


FIXTURE_PATH = Path(__file__).parents[2] / "test-fixtures" / "wft214_revive_replay.json"


def _fixture_events():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _reconstructor(events):
    initial = events[0]
    reconstructor = CombatEventReconstructor()
    reconstructor.initialize_from_snapshot({
        "player_units": copy.deepcopy(initial["player_units"]),
        "opponent_units": copy.deepcopy(initial["opponent_units"]),
    })
    return reconstructor


def _replay(events, *, through=None):
    reconstructor = _reconstructor(events)
    for event in events[1:]:
        if through is not None and event["seq"] > through:
            break
        reconstructor.process_event(event["type"], copy.deepcopy(event))
    return reconstructor


def test_fixture_covers_canonical_death_revive_order_for_both_sides():
    events = _fixture_events()
    assert [(event["seq"], event["type"]) for event in events[1:7]] == [
        (1103, "unit_attack"),
        (1104, "unit_revived"),
        (1105, "passive_triggered"),
        (1106, "effect_expired"),
        (1203, "unit_attack"),
        (1204, "unit_revived"),
    ]
    assert events[2]["unit_id"] == "opp_0"
    assert events[2]["unit_name"] == "Nicość"
    assert events[2]["post_hp"] == 480
    assert events[6]["unit_id"] == "player_0"
    assert events[6]["post_hp"] == 480

    reconstructor = _replay(events)
    players, opponents = reconstructor.get_reconstructed_state()
    assert players["player_0"]["hp"] == 480
    assert opponents["opp_0"]["hp"] == 480
    assert players["player_0"]["effects"] == []
    assert opponents["opp_0"]["effects"] == []


def test_fixture_transport_and_replay_keep_revive_contract_atomic():
    events = _fixture_events()
    revive_events = [event for event in events if event["type"] == "unit_revived"]
    assert len(revive_events) == 2

    for event in revive_events:
        payload = map_event_to_sse_payload("unit_revived", copy.deepcopy(event))
        assert payload["event_id"] == event["event_id"]
        assert payload["seq"] == event["seq"]
        assert payload["unit_id"] == event["unit_id"]
        assert payload["post_hp"] == payload["unit_hp"] == 480
        assert payload["max_hp"] == payload["unit_max_hp"] == 960
        assert payload["protection"]["expires_at"] == event["timestamp"] + 0.75

    reconstructor = _replay(events, through=1104)
    before_expiry = copy.deepcopy(reconstructor.reconstructed_opponent_units["opp_0"])
    assert before_expiry["hp"] == 480
    assert before_expiry["effects"][0]["id"] == "set2:opp_0:revive-untargetable"

    reconstructor.process_event("unit_revived", copy.deepcopy(revive_events[0]))
    assert reconstructor.reconstructed_opponent_units["opp_0"] == before_expiry

    reconstructor.process_event("effect_expired", copy.deepcopy(events[4]))
    assert reconstructor.reconstructed_opponent_units["opp_0"]["hp"] == 480
    assert reconstructor.reconstructed_opponent_units["opp_0"]["effects"] == []

    with pytest.raises(ValueError, match="conflicting duplicate"):
        reconstructor.process_event(
            "unit_revived",
            {**revive_events[0], "post_hp": 481, "unit_hp": 481},
        )


@pytest.mark.parametrize("event_type", ["unit_heal", "heal", "hp_regen", "regen_gain"])
def test_post_death_non_revive_events_fail_closed_without_hp_mutation(event_type):
    events = _fixture_events()
    reconstructor = _replay(events, through=1103)
    before = copy.deepcopy(reconstructor.reconstructed_opponent_units["opp_0"])
    payload = {
        "seq": 1110,
        "unit_id": "opp_0",
        "cause": "healing_aura",
        "post_hp": 480,
    }
    if event_type == "regen_gain":
        payload["post_hp_regen_per_sec"] = 5

    with pytest.raises(ValueError):
        reconstructor.process_event(event_type, payload)

    assert reconstructor.reconstructed_opponent_units["opp_0"] == before


@pytest.mark.parametrize(
    "field",
    [
        "event_id",
        "unit_id",
        "pre_hp",
        "post_hp",
        "max_hp",
        "timestamp",
        "cause",
        "effect_id",
        "protection",
        "effect",
    ],
)
def test_missing_revive_field_is_rejected_before_mutation(field):
    events = _fixture_events()
    reconstructor = _replay(events, through=1103)
    revive = next(event for event in events if event["seq"] == 1104)
    malformed = copy.deepcopy(revive)
    malformed.pop(field)
    before = copy.deepcopy(reconstructor.reconstructed_opponent_units["opp_0"])

    with pytest.raises(ValueError):
        reconstructor.process_event("unit_revived", malformed)

    assert reconstructor.reconstructed_opponent_units["opp_0"] == before
