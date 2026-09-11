#!/usr/bin/env python3
"""Safely rebuild the persisted opponent pool for Waffen Tactics Set 2.

The command is deliberately a dry run unless ``--apply`` and the explicit
``--confirm-wft-167`` guard are supplied.  Apply mode snapshots the SQLite
database before opening a write transaction, changes only ``opponent_teams``,
and verifies that protected player/account tables are byte-for-byte stable.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Mapping
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "waffen-tactics" / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from waffen_tactics.services.encounter_definitions import (  # noqa: E402
    DEFAULT_ENCOUNTER_SEED,
    SYSTEM_ENCOUNTER_DEFINITIONS,
    SYSTEM_USER_MAX,
    build_system_opponent_payloads,
)


DEFAULT_DB_PATH = REPO_ROOT / "waffen-tactics" / "waffen_tactics_game.db"
DEFAULT_UNITS_PATH = REPO_ROOT / "waffen-tactics" / "units.json"
MIGRATION_NAME = "WFT-167"
PROTECTED_TABLES = ("players", "leaderboard", "player_action_results")
REQUIRED_TABLE_COLUMNS = {
    "opponent_teams": {
        "id",
        "user_id",
        "nickname",
        "team_json",
        "wins",
        "losses",
        "level",
        "is_active",
    },
    "players": {"user_id", "state_json"},
}


class MigrationError(RuntimeError):
    """The database is not safe to mutate with this migration."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_canonical_units(path: Path) -> list[dict[str, Any]]:
    """Load and validate the active unit source without applying fallbacks."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationError(f"Cannot read canonical units source: {path}") from exc
    units = data.get("units") if isinstance(data, dict) else None
    if not isinstance(units, list) or not units:
        raise MigrationError("Canonical units source must contain a non-empty units list")
    if any(not isinstance(unit, dict) for unit in units):
        raise MigrationError("Canonical units source contains a non-object unit")
    ids = [unit.get("id") for unit in units]
    if any(not isinstance(unit_id, str) or not unit_id.strip() for unit_id in ids):
        raise MigrationError("Canonical units source contains a unit without a string ID")
    if len(ids) != len(set(ids)):
        raise MigrationError("Canonical units source contains duplicate unit IDs")
    if any(not isinstance(unit.get("cost"), int) for unit in units):
        raise MigrationError("Canonical units source contains a unit without an integer cost")
    return units


def _canonical_team_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        {"board": payload["board_units"], "bench": payload["bench_units"]},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _parse_team(raw: Any, canonical_ids: set[str]) -> tuple[list[str], list[str]]:
    """Return invalid IDs and structural errors for one persisted team."""

    errors: list[str] = []
    bad_ids: list[str] = []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return [], [f"malformed_json:{type(exc).__name__}"]

    if isinstance(data, list):
        board, bench = data, []
    elif isinstance(data, dict):
        board, bench = data.get("board"), data.get("bench")
        if not isinstance(board, list):
            errors.append("board_not_list")
        if not isinstance(bench, list):
            errors.append("bench_not_list")
    else:
        return [], [f"root_not_object:{type(data).__name__}"]

    for location, entries in (("board", board), ("bench", bench)):
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                errors.append(f"{location}[{index}]_not_object")
                continue
            unit_id = entry.get("unit_id")
            if not isinstance(unit_id, str) or not unit_id.strip():
                bad_ids.append("<missing>")
            elif unit_id not in canonical_ids:
                bad_ids.append(unit_id)

    return sorted(set(bad_ids)), sorted(set(errors))


def _audit_opponents(connection: sqlite3.Connection, canonical_ids: set[str]) -> dict[str, Any]:
    rows = connection.execute(
        """
        SELECT id, user_id, nickname, team_json, wins, losses, level, is_active
        FROM opponent_teams
        ORDER BY id
        """
    ).fetchall()
    invalid_id_counts: Counter[str] = Counter()
    invalid_samples: list[dict[str, Any]] = []
    invalid_row_ids: list[int] = []
    active_invalid_row_ids: list[int] = []
    active_system_user_ids: list[int] = []
    system_row_count = 0
    active_count = 0

    for row in rows:
        row_id = int(row[0])
        user_id = int(row[1] or 0)
        is_active = bool(row[7])
        if is_active:
            active_count += 1
        if user_id <= SYSTEM_USER_MAX:
            system_row_count += 1
            if is_active:
                active_system_user_ids.append(user_id)
        bad_ids, errors = _parse_team(row[3], canonical_ids)
        if not bad_ids and not errors:
            continue
        invalid_row_ids.append(row_id)
        if is_active:
            active_invalid_row_ids.append(row_id)
        for bad_id in bad_ids:
            invalid_id_counts[bad_id] += 1
        if len(invalid_samples) < 50:
            invalid_samples.append({
                "id": row_id,
                "user_id": user_id,
                "active": is_active,
                "bad_ids": bad_ids,
                "errors": errors,
            })

    return {
        "row_count": len(rows),
        "active_row_count": active_count,
        "system_row_count": system_row_count,
        "active_system_user_ids": sorted(active_system_user_ids),
        "invalid_row_count": len(invalid_row_ids),
        "active_invalid_row_count": len(active_invalid_row_ids),
        "invalid_id_counts": dict(sorted(invalid_id_counts.items())),
        "invalid_samples": invalid_samples,
        "_invalid_row_ids": invalid_row_ids,
        "_active_invalid_row_ids": active_invalid_row_ids,
    }


def _public_audit(audit: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in audit.items() if not key.startswith("_")}


def _table_digest(connection: sqlite3.Connection, table: str) -> str | None:
    if not connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone():
        return None
    columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
    digest = hashlib.sha256()
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    for row in connection.execute(f'SELECT {quoted_columns} FROM "{table}" ORDER BY rowid'):
        digest.update(json.dumps(list(row), ensure_ascii=False, default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _protected_digests(connection: sqlite3.Connection) -> dict[str, str | None]:
    return {table: _table_digest(connection, table) for table in PROTECTED_TABLES}


def _row_team_matches(row: sqlite3.Row, payload: Mapping[str, Any]) -> bool:
    try:
        actual = json.loads(row["team_json"])
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    expected = {"board": payload["board_units"], "bench": payload["bench_units"]}
    return (
        actual == expected
        and row["nickname"] == payload["nickname"]
        and int(row["wins"]) == payload["wins"]
        and int(row["losses"]) == payload["losses"]
        and int(row["level"]) == payload["level"]
    )


def _require_schema(connection: sqlite3.Connection) -> None:
    tables = {
        row[0]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    missing_tables = set(REQUIRED_TABLE_COLUMNS) - tables
    if missing_tables:
        raise MigrationError(f"Required tables are missing: {sorted(missing_tables)}")
    for table, required_columns in REQUIRED_TABLE_COLUMNS.items():
        columns = {
            row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')
        }
        missing_columns = required_columns - columns
        if missing_columns:
            raise MigrationError(
                f"Table {table} is missing required columns: {sorted(missing_columns)}"
            )


def _snapshot_database(connection: sqlite3.Connection, backup_path: Path) -> None:
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if backup_path.exists():
        raise MigrationError(f"Refusing to overwrite existing backup: {backup_path}")
    backup = sqlite3.connect(str(backup_path))
    try:
        connection.backup(backup)
        backup.commit()
    finally:
        backup.close()


def _deactivate_rows(connection: sqlite3.Connection, row_ids: Iterable[int]) -> int:
    ids = sorted(set(int(row_id) for row_id in row_ids))
    if not ids:
        return 0
    placeholders = ", ".join("?" for _ in ids)
    cursor = connection.execute(
        f"UPDATE opponent_teams SET is_active = 0 WHERE id IN ({placeholders}) AND is_active != 0",
        ids,
    )
    return cursor.rowcount


def migrate_database(
    db_path: Path,
    units_path: Path,
    *,
    seed: int = DEFAULT_ENCOUNTER_SEED,
    apply: bool = False,
    approved_revision: str | None = None,
    confirm: bool = False,
    backup_dir: Path | None = None,
) -> dict[str, Any]:
    """Audit or apply the WFT-167 migration and return a JSON-safe report."""

    if not db_path.exists():
        raise MigrationError(f"Database not found: {db_path}")
    units = load_canonical_units(units_path)
    canonical_ids = {unit["id"] for unit in units}
    payloads = build_system_opponent_payloads(units, seed=seed)

    if apply:
        if not confirm:
            raise MigrationError("Apply mode requires --confirm-wft-167")
        if not approved_revision or not re.fullmatch(r"[0-9a-fA-F]{7,40}", approved_revision):
            raise MigrationError(
                "Apply mode requires --approved-revision with a git SHA (7-40 hex characters)"
            )

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    backup_path: Path | None = None
    in_transaction = False
    try:
        _require_schema(connection)
        connection.execute("PRAGMA foreign_keys = ON")
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        if quick_check != "ok":
            raise MigrationError(f"SQLite quick_check failed: {quick_check}")

        before = _audit_opponents(connection, canonical_ids)
        protected_before = _protected_digests(connection)
        report: dict[str, Any] = {
            "migration": MIGRATION_NAME,
            "status": "dry_run" if not apply else "pending",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "approved_revision": approved_revision,
            "database": str(db_path),
            "canonical_source": {
                "path": str(units_path),
                "sha256": _sha256_file(units_path),
                "unit_count": len(units),
                "unit_ids": sorted(canonical_ids),
                "unit_ids_digest": _json_digest(sorted(canonical_ids)),
            },
            "encounter_source": {
                "definition_count": len(SYSTEM_ENCOUNTER_DEFINITIONS),
                "seed": seed,
                "system_user_ids": [definition.user_id for definition in SYSTEM_ENCOUNTER_DEFINITIONS],
            },
            "before": _public_audit(before),
            "changes": {
                "active_invalid_rows_to_quarantine": before["active_invalid_row_count"],
                "system_rows_to_rebuild": len(SYSTEM_ENCOUNTER_DEFINITIONS),
            },
        }
        if not apply:
            connection.close()
            return report

        if backup_dir is None:
            backup_dir = db_path.parent / "migration-backups"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_path = backup_dir / f"wft-167-pre-cutover-{timestamp}.db"
        _snapshot_database(connection, backup_path)

        connection.execute("BEGIN IMMEDIATE")
        in_transaction = True
        before_in_transaction = _audit_opponents(connection, canonical_ids)
        protected_before_transaction = _protected_digests(connection)
        if before_in_transaction["row_count"] != before["row_count"]:
            raise MigrationError("Opponent row count changed between audit and write lock")

        system_rows = connection.execute(
            """
            SELECT id, user_id, nickname, team_json, wins, losses, level, is_active
            FROM opponent_teams
            WHERE user_id <= ?
            ORDER BY id DESC
            """,
            (SYSTEM_USER_MAX,),
        ).fetchall()
        latest_system_by_user: dict[int, sqlite3.Row] = {}
        for row in system_rows:
            latest_system_by_user.setdefault(int(row["user_id"]), row)

        expected_by_user = {payload["user_id"]: payload for payload in payloads}
        keep_system_ids = {
            int(row["id"])
            for user_id, row in latest_system_by_user.items()
            if user_id in expected_by_user
            and bool(row["is_active"])
            and _row_team_matches(row, expected_by_user[user_id])
        }
        active_system_ids = [
            int(row["id"])
            for row in system_rows
            if bool(row["is_active"]) and int(row["id"]) not in keep_system_ids
        ]
        deactivated_count = _deactivate_rows(
            connection,
            set(active_system_ids) | set(before_in_transaction["_active_invalid_row_ids"]),
        )

        updated_system_rows = 0
        inserted_system_rows = 0
        for payload in payloads:
            row = latest_system_by_user.get(payload["user_id"])
            if row is None:
                connection.execute(
                    """
                    INSERT INTO opponent_teams
                        (user_id, nickname, team_json, wins, losses, level, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        payload["user_id"],
                        payload["nickname"],
                        _canonical_team_json(payload),
                        payload["wins"],
                        payload["losses"],
                        payload["level"],
                    ),
                )
                inserted_system_rows += 1
                continue
            if bool(row["is_active"]) and _row_team_matches(row, payload):
                continue
            connection.execute(
                """
                UPDATE opponent_teams
                SET nickname = ?, team_json = ?, wins = ?, losses = ?, level = ?,
                    is_active = 1, created_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    payload["nickname"],
                    _canonical_team_json(payload),
                    payload["wins"],
                    payload["losses"],
                    payload["level"],
                    row["id"],
                ),
            )
            updated_system_rows += 1

        after = _audit_opponents(connection, canonical_ids)
        protected_after = _protected_digests(connection)
        active_system_users = set(after["active_system_user_ids"])
        expected_system_users = {
            definition.user_id for definition in SYSTEM_ENCOUNTER_DEFINITIONS
        }
        if after["active_invalid_row_count"] != 0:
            raise MigrationError("Active opponent rows still contain invalid Set 2 data")
        if active_system_users != expected_system_users:
            raise MigrationError(
                "Active system-opponent IDs do not match the encounter definitions"
            )
        if protected_after != protected_before_transaction:
            raise MigrationError("A protected player/account table changed during migration")

        connection.commit()
        in_transaction = False
        backup_sha256 = _sha256_file(backup_path)
        report.update({
            "status": "applied",
            "before": _public_audit(before_in_transaction),
            "after": _public_audit(after),
            "backup": {"path": str(backup_path), "sha256": backup_sha256},
            "changes": {
                "active_invalid_rows_before": before_in_transaction["active_invalid_row_count"],
                "deactivated_row_count": deactivated_count,
                "updated_system_rows": updated_system_rows,
                "inserted_system_rows": inserted_system_rows,
                "protected_tables_unchanged": True,
            },
            "verification": {
                "active_invalid_row_count": after["active_invalid_row_count"],
                "active_system_definition_count": len(expected_system_users),
                "active_system_user_ids_match": active_system_users == expected_system_users,
                "protected_table_digests_match": protected_after == protected_before_transaction,
                "pre_transaction_protected_digests_match": protected_before_transaction == protected_before,
            },
        })
        return report
    except Exception:
        if in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--units", type=Path, default=DEFAULT_UNITS_PATH)
    parser.add_argument("--seed", type=int, default=DEFAULT_ENCOUNTER_SEED)
    parser.add_argument("--apply", action="store_true", help="Apply after backup; otherwise audit only")
    parser.add_argument("--confirm-wft-167", action="store_true", help="Required with --apply")
    parser.add_argument("--approved-revision", help="Approved git SHA required with --apply")
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--report", type=Path, help="Write the JSON report to this path")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = migrate_database(
            args.db,
            args.units,
            seed=args.seed,
            apply=args.apply,
            approved_revision=args.approved_revision,
            confirm=args.confirm_wft_167,
            backup_dir=args.backup_dir,
        )
    except MigrationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
