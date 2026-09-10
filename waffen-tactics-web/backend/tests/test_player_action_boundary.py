import asyncio
import sqlite3
import time

import pytest

from waffen_tactics.models.player_state import PlayerState
from waffen_tactics.services.database import (
    DatabaseManager,
    InvalidStoredPlayerStateError,
    PlayerActionConflictError,
)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def database(tmp_path):
    db = DatabaseManager(str(tmp_path / "actions.sqlite3"))
    _run(db.initialize())
    _run(db.save_player(PlayerState(user_id=42, gold=10)))
    return db


def _parallel(*calls):
    async def run():
        return await asyncio.gather(*(asyncio.to_thread(call) for call in calls))

    return _run(run())


def test_two_different_mutations_are_serialized(database):
    def spend_one(player):
        time.sleep(0.03)
        player.gold -= 1
        return True, "spent one"

    results = _parallel(
        lambda: _run(database.apply_player_action(42, "spend_one", spend_one)),
        lambda: _run(database.apply_player_action(42, "spend_one", spend_one)),
    )

    assert [result[0] for result in results] == [True, True]
    player = _run(database.load_player(42))
    assert player.gold == 8


def test_duplicate_idempotency_key_executes_once_and_returns_original_state(database):
    executions = 0

    def reward(player):
        nonlocal executions
        executions += 1
        time.sleep(0.03)
        player.gold += 5
        player.round_number += 1
        return True, "reward granted"

    results = _parallel(
        lambda: _run(database.apply_player_action(42, "combat_result", reward, "combat-42")),
        lambda: _run(database.apply_player_action(42, "combat_result", reward, "combat-42")),
    )

    assert executions == 1
    assert results[0][0:2] == (True, "reward granted")
    assert results[1][0:2] == (True, "reward granted")
    assert results[0][2].gold == results[1][2].gold == 15
    assert results[0][2].round_number == results[1][2].round_number == 2
    stored = _run(database.load_player(42))
    assert (stored.gold, stored.round_number) == (15, 2)


def test_idempotency_key_cannot_change_action_identity(database):
    def mutation(player):
        player.gold += 1
        return True, "ok"

    _run(database.apply_player_action(42, "buy_xp", mutation, "same-key"))

    with pytest.raises(PlayerActionConflictError, match="already belongs"):
        _run(database.apply_player_action(42, "reroll_shop", mutation, "same-key"))

    stored = _run(database.load_player(42))
    assert stored.gold == 11


def test_invalid_state_json_is_rejected_instead_of_saved_or_loaded(database):
    connection = sqlite3.connect(database.db_path)
    connection.execute(
        "UPDATE players SET state_json = ? WHERE user_id = ?",
        ("{truncated", 42),
    )
    connection.commit()
    connection.close()

    with pytest.raises(InvalidStoredPlayerStateError):
        _run(database.load_player(42))


def test_duplicate_combat_commit_returns_one_result_identity(database):
    initial = _run(database.load_player(42))
    expected = database._serialize_player(initial)
    first = PlayerState.from_dict(initial.to_dict())
    second = PlayerState.from_dict(initial.to_dict())
    first.gold += 5
    first.round_number += 1
    second.gold += 5
    second.round_number += 1

    results = _parallel(
        lambda: _run(database.commit_player_state_action(
            42, "combat", first, expected, "combat-retry", "result-123",
            {"winner": "team_a"},
        )),
        lambda: _run(database.commit_player_state_action(
            42, "combat", second, expected, "combat-retry", "result-123",
            {"winner": "team_a"},
        )),
    )

    assert sorted(result['committed'] for result in results) == [False, True]
    assert {result['result_id'] for result in results} == {'result-123'}
    assert {result['result']['winner'] for result in results} == {'team_a'}
    stored = _run(database.load_player(42))
    assert (stored.gold, stored.round_number) == (15, 2)


def test_stale_different_combat_commit_is_explicit_conflict(database):
    initial = _run(database.load_player(42))
    expected = database._serialize_player(initial)
    first = PlayerState.from_dict(initial.to_dict())
    second = PlayerState.from_dict(initial.to_dict())
    first.gold += 5
    second.gold += 7

    _run(database.commit_player_state_action(
        42, "combat", first, expected, "combat-one", "result-one",
        {"winner": "team_a"},
    ))
    with pytest.raises(PlayerActionConflictError, match="changed while action"):
        _run(database.commit_player_state_action(
            42, "combat", second, expected, "combat-two", "result-two",
            {"winner": "team_b"},
        ))

    stored = _run(database.load_player(42))
    assert stored.gold == 15
