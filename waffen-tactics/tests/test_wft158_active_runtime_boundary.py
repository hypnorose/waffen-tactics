import json

import pytest

from waffen_tactics.models.player_state import PlayerState, UnitInstance
from waffen_tactics.services.data_loader import DATA_FILE, TRAITS_FILE, load_game_data
from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.services.set2_contract import validate_active_set2_dataset
from waffen_tactics.services.unit_manager import UnitManager


def test_active_set2_loader_exposes_only_cross_resolved_canonical_content():
    data = load_game_data()
    units = json.loads(DATA_FILE.read_text(encoding="utf-8"))["units"]
    traits = json.loads(TRAITS_FILE.read_text(encoding="utf-8"))["traits"]

    assert len(data.units) == 32
    assert len(data.traits) == 12
    assert validate_active_set2_dataset(units, traits) == []
    active_trait_names = {trait["name"] for trait in traits}
    assert all(
        trait_name in active_trait_names
        for unit in units
        for trait_name in unit["traits"]
    )


def test_active_dataset_rejects_unit_trait_that_is_not_in_active_source():
    units = [{"id": "unit", "traits": ["Removed Legacy Trait"]}]
    traits = [{"id": "trait", "name": "Active Trait"}]

    errors = validate_active_set2_dataset(
        units,
        traits,
        expected_unit_count=1,
        expected_trait_count=1,
    )

    assert any("unknown active Set 2 trait" in error for error in errors)


def test_board_synergy_resolution_fails_closed_for_stale_saved_unit_id():
    game_manager = GameManager()
    player = PlayerState(
        user_id=158,
        board=[UnitInstance(unit_id="legacy_unit_id")],
    )

    with pytest.raises(ValueError, match=r"Unknown active Set 2 board\[0\] id"):
        game_manager.get_board_synergies(player)


def test_locked_shop_resolution_fails_closed_for_stale_saved_unit_id():
    game_manager = GameManager()
    player = PlayerState(
        user_id=159,
        last_shop=["legacy_unit_id"],
        locked_shop=True,
    )

    with pytest.raises(ValueError, match=r"Unknown active Set 2 shop\[0\] id"):
        game_manager.generate_shop(player)


def test_direct_unit_manager_move_does_not_mutate_stale_unit():
    game_manager = GameManager()
    player = PlayerState(user_id=160)
    stale = UnitInstance(unit_id="legacy_unit_id", instance_id="stale-instance")
    player.bench.append(stale)

    success, message = UnitManager(game_manager.data).move_to_board(
        player,
        stale.instance_id,
    )

    assert success is False
    assert "Błąd danych jednostki" in message
    assert player.bench == [stale]
    assert player.board == []
