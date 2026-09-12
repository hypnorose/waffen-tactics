import contextlib
import io
import json
from pathlib import Path

from services.combat_service import run_combat_simulation
from waffen_tactics.services.combat_unit import CombatUnit


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "wft181_jaeger_attack.json"


class FixtureStats:
    def __init__(self, hp, mana_on_attack):
        self.hp = hp
        self.mana_on_attack = mana_on_attack


def _make_unit(data):
    unit = CombatUnit(
        id=data["id"],
        name=data["name"],
        hp=data["hp"],
        attack=data["attack"],
        defense=data["defense"],
        attack_speed=data["attack_speed"],
        max_mana=data["max_mana"],
        stats=FixtureStats(data["max_hp"], data["mana_on_attack"]),
        position=data["position"],
    )
    unit.mana = data["current_mana"]
    return unit


def test_wft181_attack_damage_event_precedes_following_mana_or_snapshot():
    """The artifact's 750 -> 723 hit must remain replayable from one event."""
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    expected = fixture["expected_attack"]

    player_units = [_make_unit(data) for data in fixture["player_units"]]
    opponent_units = [_make_unit(data) for data in fixture["opponent_units"]]

    # The fixture has one target on each side, so no random targeting is needed.
    # Keep the runtime flag deterministic if the selector changes in the future.
    import os

    previous_targeting = os.environ.get("WAFFEN_DETERMINISTIC_TARGETING")
    os.environ["WAFFEN_DETERMINISTIC_TARGETING"] = "1"
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            result = run_combat_simulation(
                player_units,
                opponent_units,
                skip_per_round_buffs=True,
                skip_per_second_buffs=False,
                attach_game_state=True,
            )
    finally:
        if previous_targeting is None:
            os.environ.pop("WAFFEN_DETERMINISTIC_TARGETING", None)
        else:
            os.environ["WAFFEN_DETERMINISTIC_TARGETING"] = previous_targeting

    events = result["events"]
    animation_index = next(
        index
        for index, (event_type, payload) in enumerate(events)
        if event_type == "animation_start"
        and payload.get("attacker_id") == expected["attacker_id"]
        and payload.get("target_id") == expected["target_id"]
    )
    attack_index, attack = next(
        (index, payload)
        for index, (event_type, payload) in enumerate(events)
        if event_type == "unit_attack"
        and payload.get("attacker_id") == expected["attacker_id"]
        and payload.get("target_id") == expected["target_id"]
        and payload.get("pre_hp") == expected["pre_hp"]
    )

    assert animation_index < attack_index
    for event_type, payload in events[animation_index + 1 : attack_index]:
        if event_type in {"state_snapshot", "mana_update"}:
            jaeger = next(
                unit
                for unit in payload["game_state"]["player_units"]
                if unit["id"] == expected["target_id"]
            )
            assert jaeger["hp"] == expected["pre_hp"]

    for field, value in expected.items():
        assert attack[field] == value

    jaeger_after_attack = next(
        unit
        for unit in attack["game_state"]["player_units"]
        if unit["id"] == expected["target_id"]
    )
    assert jaeger_after_attack["hp"] == expected["post_hp"]
