import asyncio
import json
import sqlite3
from pathlib import Path

from scripts.rebuild_set2_opponents import (
    DEFAULT_ENCOUNTER_SEED,
    DEFAULT_UNITS_PATH,
    SYSTEM_ENCOUNTER_DEFINITIONS,
    migrate_database,
)
from waffen_tactics.services.database import DatabaseManager


def _create_database(path):
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE players (
            user_id INTEGER PRIMARY KEY,
            state_json TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE opponent_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            nickname TEXT NOT NULL,
            team_json TEXT NOT NULL,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            avatar TEXT DEFAULT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            nickname TEXT NOT NULL,
            wins INTEGER NOT NULL,
            losses INTEGER NOT NULL,
            level INTEGER NOT NULL,
            round_number INTEGER NOT NULL,
            team_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE player_action_results (
            user_id INTEGER NOT NULL,
            action_key TEXT NOT NULL,
            action_name TEXT NOT NULL,
            success INTEGER NOT NULL,
            message TEXT NOT NULL,
            state_json TEXT,
            PRIMARY KEY (user_id, action_key)
        );
        """
    )
    connection.commit()
    connection.close()


def _insert_opponent(path, user_id, nickname, team, is_active=1):
    connection = sqlite3.connect(path)
    connection.execute(
        """
        INSERT INTO opponent_teams
            (user_id, nickname, team_json, wins, losses, level, is_active)
        VALUES (?, ?, ?, 1, 1, 1, ?)
        """,
        (user_id, nickname, json.dumps(team), is_active),
    )
    connection.commit()
    connection.close()


def test_system_payloads_are_deterministic_and_use_only_supplied_units():
    from waffen_tactics.services.encounter_definitions import build_system_opponent_payloads

    units = [
        {"id": "set2_a", "cost": 1},
        {"id": "set2_b", "cost": 2},
        {"id": "set2_c", "cost": 3},
        {"id": "set2_d", "cost": 5},
    ]
    first = build_system_opponent_payloads(units, seed=DEFAULT_ENCOUNTER_SEED)
    second = build_system_opponent_payloads(units, seed=DEFAULT_ENCOUNTER_SEED)

    assert first == second
    allowed = {unit["id"] for unit in units}
    assert len(first) == len(SYSTEM_ENCOUNTER_DEFINITIONS)
    assert all(
        entry["unit_id"] in allowed
        for payload in first
        for entry in payload["board_units"]
    )


def test_dry_run_does_not_mutate_database(tmp_path):
    database = tmp_path / "game.sqlite3"
    _create_database(database)
    _insert_opponent(
        database,
        1,
        "old bot",
        {"board": [{"unit_id": "mrvlook", "star_level": 1}], "bench": []},
    )
    before = sqlite3.connect(database).execute(
        "SELECT user_id, team_json, is_active FROM opponent_teams"
    ).fetchall()

    report = migrate_database(
        database,
        DEFAULT_UNITS_PATH,
    )

    assert report["status"] == "dry_run"
    assert report["before"]["active_invalid_row_count"] == 1
    after = sqlite3.connect(database).execute(
        "SELECT user_id, team_json, is_active FROM opponent_teams"
    ).fetchall()
    assert after == before


def test_apply_quarantines_invalid_rows_rebuilds_system_pool_and_preserves_accounts(tmp_path):
    database = tmp_path / "game.sqlite3"
    backup_dir = tmp_path / "backups"
    _create_database(database)
    player_state = '{"user_id": 42, "wins": 3, "losses": 1}'
    connection = sqlite3.connect(database)
    connection.execute(
        "INSERT INTO players(user_id, state_json) VALUES (?, ?)", (42, player_state)
    )
    connection.execute(
        """
        INSERT INTO leaderboard
            (user_id, nickname, wins, losses, level, round_number, team_json)
        VALUES (42, 'player', 3, 1, 1, 4, '{}')
        """
    )
    connection.execute(
        """
        INSERT INTO player_action_results
            (user_id, action_key, action_name, success, message, state_json)
        VALUES (42, 'key', 'action', 1, 'ok', ?)
        """,
        (player_state,),
    )
    connection.commit()
    connection.close()
    _insert_opponent(
        database,
        1,
        "old system",
        {"board": [{"unit_id": "mrvlook", "star_level": 1}], "bench": []},
    )
    _insert_opponent(
        database,
        200001,
        "stale player",
        {"board": [{"unit_id": "mrvlook", "star_level": 1}], "bench": []},
    )
    _insert_opponent(
        database,
        200002,
        "valid player",
        {"board": [{"unit_id": "yossarian", "star_level": 1}], "bench": []},
    )

    report = migrate_database(
        database,
        __import__("pathlib").Path("waffen-tactics/units.json"),
        apply=True,
        approved_revision="a" * 40,
        confirm=True,
        backup_dir=backup_dir,
    )

    expected_system_ids = {
        definition.user_id for definition in SYSTEM_ENCOUNTER_DEFINITIONS
    }
    assert report["status"] == "applied"
    assert report["after"]["active_invalid_row_count"] == 0
    assert set(report["after"]["active_system_user_ids"]) == expected_system_ids
    assert report["verification"]["protected_table_digests_match"] is True
    assert report["backup"]["sha256"]
    assert Path(report["backup"]["path"]).exists()

    connection = sqlite3.connect(database)
    assert connection.execute(
        "SELECT state_json FROM players WHERE user_id = 42"
    ).fetchone()[0] == player_state
    assert connection.execute(
        "SELECT is_active FROM opponent_teams WHERE user_id = 200001"
    ).fetchone()[0] == 0
    assert connection.execute(
        "SELECT is_active FROM opponent_teams WHERE user_id = 200002"
    ).fetchone()[0] == 1
    connection.close()

    rerun = migrate_database(
        database,
        DEFAULT_UNITS_PATH,
        apply=True,
        approved_revision="a" * 40,
        confirm=True,
        backup_dir=backup_dir / "rerun",
    )
    assert rerun["changes"]["updated_system_rows"] == 0
    assert rerun["changes"]["inserted_system_rows"] == 0
    assert rerun["after"]["active_invalid_row_count"] == 0


def test_system_selection_ignores_deactivated_snapshots(tmp_path):
    database = tmp_path / "selection.sqlite3"
    manager = DatabaseManager(str(database))
    asyncio.run(manager.initialize())
    _insert_opponent(
        database,
        1,
        "inactive stale",
        {"board": [{"unit_id": "mrvlook", "star_level": 1}], "bench": []},
        is_active=0,
    )
    _insert_opponent(
        database,
        2,
        "active set2",
        {"board": [{"unit_id": "yossarian", "star_level": 1}], "bench": []},
        is_active=1,
    )

    selected = asyncio.run(manager.get_random_system_opponent())

    assert selected["user_id"] == 2
    assert selected["board"][0]["unit_id"] == "yossarian"
