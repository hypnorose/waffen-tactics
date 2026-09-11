import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "waffen-tactics", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from routes.game_state_utils import PlayerStateEnrichmentError, enrich_player_state
from services.combat_service import InvalidCombatInputError, resolve_persisted_team_units
from waffen_tactics.models.player_state import PlayerState, UnitInstance


@pytest.mark.parametrize(
    "state",
    [
        PlayerState(user_id=158, board=[UnitInstance(unit_id="legacy_unit_id")]),
        PlayerState(user_id=159, bench=[UnitInstance(unit_id="legacy_unit_id")]),
        PlayerState(user_id=160, last_shop=["legacy_unit_id"]),
    ],
)
def test_player_state_projection_rejects_stale_unit_ids(state):
    with pytest.raises(PlayerStateEnrichmentError) as raised:
        enrich_player_state(state)

    assert raised.value.stage == "active_roster"


def test_combat_team_resolution_rejects_stale_saved_unit_id():
    with pytest.raises(InvalidCombatInputError, match="Unknown player unit"):
        resolve_persisted_team_units(
            [{"unit_id": "legacy_unit_id", "star_level": 1}],
            "player",
            require_saved_entries=True,
        )
