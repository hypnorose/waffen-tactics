import asyncio
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from scripts.reset_production_database import (
    DEFAULT_UNITS_PATH,
    ResetError,
    reset_database,
)
from waffen_tactics.services.database import DatabaseManager


def _initialize_database(path: Path) -> None:
    asyncio.run(DatabaseManager(str(path)).initialize())


def _insert_legacy_rows(path: Path) -> None:
    connection = sqlite3.connect(path)
    state = json.dumps({"user_id": 42, "bench": [{"items": ["sugar_rush"]}]})
    connection.execute("INSERT INTO players(user_id, state_json) VALUES (?, ?)", (42, state))
    connection.execute(
        """
        INSERT INTO leaderboard
            (user_id, nickname, wins, losses, level, round_number, team_json)
        VALUES (42, 'player', 2, 1, 1, 3, '{}')
        """
    )
    connection.execute(
        """
        INSERT INTO player_action_results
            (user_id, action_key, action_name, success, message, state_json, result_json)
        VALUES (42, 'combat:42:1', 'combat', 1, 'ok', ?, ?)
        """,
        (state, json.dumps({"item": "fortified_vault"})),
    )
    connection.execute(
        """
        INSERT INTO opponent_teams
            (user_id, nickname, team_json, wins, losses, level, is_active)
        VALUES (200001, 'old player', ?, 1, 0, 1, 1)
        """,
        (json.dumps({"board": [{"unit_id": "mrvlook", "star_level": 1}], "bench": []}),),
    )
    connection.commit()
    connection.close()


def _counts(path: Path) -> dict[str, int]:
    connection = sqlite3.connect(path)
    try:
        return {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in ("players", "leaderboard", "player_action_results", "opponent_teams")
        }
    finally:
        connection.close()


def test_dry_run_does_not_mutate_database(tmp_path):
    database = tmp_path / "game.sqlite3"
    _initialize_database(database)
    _insert_legacy_rows(database)
    before = _counts(database)

    report = reset_database(database, DEFAULT_UNITS_PATH)

    assert report["status"] == "dry_run"
    assert report["before"]["table_counts"] == before
    assert _counts(database) == before


def test_apply_requires_explicit_confirmation_and_revision(tmp_path):
    database = tmp_path / "game.sqlite3"
    _initialize_database(database)

    with pytest.raises(ResetError, match="confirm-wft-169"):
        reset_database(database, DEFAULT_UNITS_PATH, apply=True, approved_revision="a" * 40)
    with pytest.raises(ResetError, match="approved-revision"):
        reset_database(database, DEFAULT_UNITS_PATH, apply=True, confirm=True)


def test_apply_creates_clean_database_and_verified_backup(tmp_path):
    database = tmp_path / "game.sqlite3"
    backup_dir = tmp_path / "backups"
    _initialize_database(database)
    _insert_legacy_rows(database)

    report = reset_database(
        database,
        DEFAULT_UNITS_PATH,
        apply=True,
        confirm=True,
        approved_revision="a" * 40,
        backup_dir=backup_dir,
    )

    assert report["status"] == "applied"
    assert report["changes"]["removed_rows"] == {
        "players": 1,
        "leaderboard": 1,
        "player_action_results": 1,
        "opponent_teams": 1,
    }
    assert _counts(database) == {
        "players": 0,
        "leaderboard": 0,
        "player_action_results": 0,
        "opponent_teams": 38,
    }
    connection = sqlite3.connect(database)
    try:
        assert [row[0] for row in connection.execute(
            "SELECT user_id FROM opponent_teams WHERE is_active = 1 ORDER BY user_id"
        )] == list(range(1, 39))
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    finally:
        connection.close()

    backup_path = Path(report["backup"]["path"])
    assert backup_path.exists()
    assert hashlib.sha256(backup_path.read_bytes()).hexdigest() == report["backup"]["sha256"]
    assert _counts(backup_path) == {
        "players": 1,
        "leaderboard": 1,
        "player_action_results": 1,
        "opponent_teams": 1,
    }
    assert report["verification"]["final_database_valid"] is True
    assert report["verification"]["legacy_item_ids_mapped"] is False
