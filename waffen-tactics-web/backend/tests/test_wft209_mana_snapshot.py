import pytest

from routes.game_combat import map_event_to_sse_payload
from services.combat_event_reconstructor import CombatEventReconstructor
from services.combat_snapshot_contract import CombatSnapshotContractError
from services.combat_service import run_combat_simulation
from waffen_tactics.models.unit import CombatUnitStats
from waffen_tactics.services.combat_unit import CombatUnit


def _snapshot(mana=12):
    unit = {
        "id": "opp_5",
        "name": "Uhla",
        "hp": 100,
        "max_hp": 100,
        "current_mana": mana,
        "max_mana": 80,
        "shield": 0,
        "effects": [],
    }
    return {"player_units": [dict(unit, id="player")], "opponent_units": [unit]}


def test_sse_rejects_mana_event_when_embedded_snapshot_disagrees():
    with pytest.raises(CombatSnapshotContractError, match=r"unit_id=opp_5.*current_mana"):
        map_event_to_sse_payload(
            "mana_update",
            {
                "unit_id": "opp_5",
                "current_mana": 16,
                "post_mana": 16,
                "amount": 10,
                "seq": 188,
                "event_id": "combat:188",
                "game_state": _snapshot(mana=12),
            },
        )


def test_replay_rejects_mana_event_before_mutating_state():
    reconstructor = CombatEventReconstructor()
    reconstructor.initialize_from_snapshot(_snapshot(mana=12))

    with pytest.raises(CombatSnapshotContractError, match=r"unit_id=opp_5"):
        reconstructor.process_event(
            "mana_update",
            {
                "unit_id": "opp_5",
                "current_mana": 16,
                "post_mana": 16,
                "amount": 10,
                "seq": 188,
                "event_id": "combat:188",
                "game_state": _snapshot(mana=12),
            },
        )

    assert reconstructor.reconstructed_opponent_units["opp_5"]["current_mana"] == 12


def _make_unit(unit_id, *, hp=100, attack=10, attack_speed=1.0, max_mana=100, passive=None):
    stats = CombatUnitStats(
        hp=hp,
        attack=attack,
        defense=0,
        max_mana=max_mana,
        attack_speed=attack_speed,
        mana_on_attack=10,
        mana_regen=0,
    )
    return CombatUnit(
        id=unit_id,
        name=unit_id,
        hp=hp,
        attack=attack,
        defense=0,
        attack_speed=attack_speed,
        max_mana=max_mana,
        mana_regen=0,
        stats=stats,
        position="front",
        passive=passive,
    )


def test_uhla_transfer_preserves_post_mana_checkpoint_and_same_timestamp_order():
    uhla = _make_unit(
        "uhla",
        passive={
            "id": "set2.passive.uhla",
            "runtime": {"type": "mana_transfer", "percent": 40, "cap": 5},
        },
    )
    ally = _make_unit("ally")
    target = _make_unit("target", hp=100000, attack=0, attack_speed=0.0)
    # Match the reported reproduction: Uhla starts at 6, gains 10 from the
    # attack, then transfers 4 away and ends that timestamp at 12.
    uhla.mana = 6

    result = run_combat_simulation(
        [uhla, ally],
        [target],
        skip_per_round_buffs=True,
        skip_per_second_buffs=True,
        attach_game_state=True,
    )

    mana_events = [
        (event_type, payload)
        for event_type, payload in result["events"]
        if event_type == "mana_update"
    ]
    assert mana_events

    for _, payload in mana_events:
        unit = next(
            unit
            for side in ("player_units", "opponent_units")
            for unit in payload["game_state"][side]
            if unit["id"] == payload["unit_id"]
        )
        assert unit["current_mana"] == payload["current_mana"]
        if payload.get("post_mana") is not None:
            assert unit["current_mana"] == payload["post_mana"]

    same_timestamp = [
        payload
        for _, payload in mana_events
        if payload["unit_id"] == "uhla" and payload["timestamp"] == 1.2
    ]
    gain = next(payload for payload in same_timestamp if payload["amount"] == 10)
    transfer = next(payload for payload in same_timestamp if payload["amount"] == -4)
    assert gain["current_mana"] == 16
    assert gain["seq"] < transfer["seq"]
    assert transfer["current_mana"] == 12
