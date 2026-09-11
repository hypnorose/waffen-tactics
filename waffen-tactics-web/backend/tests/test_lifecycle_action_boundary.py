import asyncio
import sqlite3
import time

import pytest

from waffen_tactics.models.player_state import PlayerState, UnitInstance
from waffen_tactics.services.database import DatabaseManager


def _run(coro):
    return asyncio.run(coro)


def _parallel(*calls):
    async def run():
        return await asyncio.gather(*(asyncio.to_thread(call) for call in calls))

    return _run(run())


@pytest.fixture
def database(tmp_path):
    db = DatabaseManager(str(tmp_path / 'lifecycle.sqlite3'))
    _run(db.initialize())
    _run(db.save_player(PlayerState(user_id=42, gold=10)))
    return db


def test_lifecycle_and_regular_actions_cannot_overwrite_each_other(database):
    def lifecycle_mutation(player):
        time.sleep(0.03)
        player.gold += 1
        return True, 'lifecycle mutation', player, None

    def regular_mutation(player):
        time.sleep(0.03)
        player.gold += 1
        return True, 'regular mutation'

    results = _parallel(
        lambda: _run(database.apply_player_lifecycle_action(
            42, 'start_game', lifecycle_mutation, 'start-race'
        )),
        lambda: _run(database.apply_player_action(
            42, 'buy_xp', regular_mutation, 'action-race'
        )),
    )

    assert [result[0] for result in results] == [True, True]
    stored = _run(database.load_player(42))
    assert stored.gold == 12


def test_start_retry_creates_missing_player_once(database):
    _run(database.delete_player(42))
    executions = 0

    def start_mutation(player):
        nonlocal executions
        executions += 1
        assert player is None
        time.sleep(0.03)
        return True, 'started', PlayerState(user_id=42), None

    results = _parallel(
        lambda: _run(database.apply_player_lifecycle_action(
            42, 'start_game', start_mutation, 'start-retry'
        )),
        lambda: _run(database.apply_player_lifecycle_action(
            42, 'start_game', start_mutation, 'start-retry'
        )),
    )

    assert executions == 1
    assert [result[:2] for result in results] == [(True, 'started'), (True, 'started')]
    assert _run(database.load_player(42)) is not None


def test_reset_retry_returns_one_committed_result(database):
    executions = 0

    def reset_mutation(player):
        nonlocal executions
        executions += 1
        time.sleep(0.03)
        return True, 'reset', PlayerState(user_id=42), None

    results = _parallel(
        lambda: _run(database.apply_player_lifecycle_action(
            42, 'reset_game', reset_mutation, 'reset-retry'
        )),
        lambda: _run(database.apply_player_lifecycle_action(
            42, 'reset_game', reset_mutation, 'reset-retry'
        )),
    )

    assert executions == 1
    assert [result[:2] for result in results] == [(True, 'reset'), (True, 'reset')]
    stored = _run(database.load_player(42))
    assert (stored.gold, stored.round_number) == (10, 1)


def test_surrender_retry_commits_player_reset_and_leaderboard_once(database):
    initial = PlayerState(
        user_id=42,
        wins=4,
        losses=2,
        level=3,
        round_number=8,
        board=[UnitInstance(unit_id='rifleman', star_level=2)],
    )
    _run(database.save_player(initial))
    executions = 0

    def surrender_mutation(player):
        nonlocal executions
        executions += 1
        time.sleep(0.03)
        leaderboard_entry = {
            'user_id': 42,
            'nickname': 'TestPlayer',
            'wins': player.wins,
            'losses': player.losses,
            'level': player.level,
            'round_number': player.round_number,
            'team_units': [
                {'unit_id': unit.unit_id, 'star_level': unit.star_level}
                for unit in player.board
            ],
        }
        return True, 'surrendered', PlayerState(user_id=42), leaderboard_entry

    results = _parallel(
        lambda: _run(database.apply_player_lifecycle_action(
            42, 'surrender_game', surrender_mutation, 'surrender-retry'
        )),
        lambda: _run(database.apply_player_lifecycle_action(
            42, 'surrender_game', surrender_mutation, 'surrender-retry'
        )),
    )

    assert executions == 1
    assert [result[:2] for result in results] == [(True, 'surrendered'), (True, 'surrendered')]
    stored = _run(database.load_player(42))
    assert (stored.wins, stored.losses, stored.round_number) == (0, 0, 1)

    connection = sqlite3.connect(database.db_path)
    leaderboard_count = connection.execute(
        'SELECT COUNT(*) FROM leaderboard WHERE user_id = 42'
    ).fetchone()[0]
    ledger_count = connection.execute(
        "SELECT COUNT(*) FROM player_action_results WHERE user_id = 42 AND action_key = 'surrender-retry'"
    ).fetchone()[0]
    connection.close()
    assert leaderboard_count == 1
    assert ledger_count == 1
