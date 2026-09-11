#!/usr/bin/env python3
"""Build a clean production database for WFT-169.

The command is read-only by default.  Apply mode requires both the explicit
``--confirm-wft-169`` guard and an approved git revision.  It creates and
verifies a brand-new SQLite database, keeps a verified backup of the current
database, then atomically swaps the new database into place.

This reset intentionally removes player saves, leaderboard history,
idempotency/action results, and every historical opponent snapshot.  The only
rows seeded into the replacement database are the canonical Set 2 system
encounters produced by the shared encounter definitions.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import uuid
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "waffen-tactics" / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from waffen_tactics.services.database import DatabaseManager  # noqa: E402
from waffen_tactics.services.encounter_definitions import (  # noqa: E402
    DEFAULT_ENCOUNTER_SEED,
    SYSTEM_ENCOUNTER_DEFINITIONS,
    SYSTEM_USER_MAX,
    build_system_opponent_payloads,
)
from scripts.rebuild_set2_opponents import (  # noqa: E402
    MigrationError as OpponentMigrationError,
    load_canonical_units,
)


DEFAULT_DB_PATH = REPO_ROOT / "waffen-tactics" / "waffen_tactics_game.db"
DEFAULT_UNITS_PATH = REPO_ROOT / "waffen-tactics" / "units.json"
MIGRATION_NAME = "WFT-169"
PROTECTED_RESET_TABLES = ("players", "leaderboard", "player_action_results")
REQUIRED_TABLES = PROTECTED_RESET_TABLES + ("opponent_teams",)
SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")


class ResetError(RuntimeError):
    """The reset cannot safely continue."""


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


def _canonical_team_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        {"board": payload["board_units"], "bench": payload["bench_units"]},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }


def _require_tables(connection: sqlite3.Connection) -> None:
    missing = set(REQUIRED_TABLES) - _table_names(connection)
    if missing:
        raise ResetError(f"Database is missing required tables: {sorted(missing)}")


def _quick_check(connection: sqlite3.Connection) -> str:
    return str(connection.execute("PRAGMA quick_check").fetchone()[0])


def _table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        for table in REQUIRED_TABLES
    }


def _active_system_ids(connection: sqlite3.Connection) -> list[int]:
    return [
        int(row[0])
        for row in connection.execute(
            """
            SELECT user_id
            FROM opponent_teams
            WHERE user_id <= ? AND is_active = 1
            ORDER BY user_id
            """,
            (SYSTEM_USER_MAX,),
        )
    ]


def _invalid_opponent_ids(
    connection: sqlite3.Connection,
    canonical_ids: set[str],
) -> dict[str, int]:
    invalid: Counter[str] = Counter()
    rows = connection.execute("SELECT team_json FROM opponent_teams").fetchall()
    for (raw_team,) in rows:
        try:
            team = json.loads(raw_team)
        except (TypeError, ValueError, json.JSONDecodeError):
            invalid["<malformed_json>"] += 1
            continue
        if not isinstance(team, dict):
            invalid["<invalid_root>"] += 1
            continue
        for location in ("board", "bench"):
            entries = team.get(location)
            if not isinstance(entries, list):
                invalid[f"<{location}_not_list>"] += 1
                continue
            for entry in entries:
                unit_id = entry.get("unit_id") if isinstance(entry, dict) else None
                if unit_id not in canonical_ids:
                    invalid[str(unit_id or "<missing>")] += 1
    return dict(sorted(invalid.items()))


def _inventory(
    connection: sqlite3.Connection,
    canonical_ids: set[str],
) -> dict[str, Any]:
    _require_tables(connection)
    quick_check = _quick_check(connection)
    counts = _table_counts(connection)
    system_ids = _active_system_ids(connection)
    invalid_ids = _invalid_opponent_ids(connection, canonical_ids)
    non_system_count = int(
        connection.execute(
            "SELECT COUNT(*) FROM opponent_teams WHERE user_id > ?",
            (SYSTEM_USER_MAX,),
        ).fetchone()[0]
    )
    active_count = int(
        connection.execute(
            "SELECT COUNT(*) FROM opponent_teams WHERE is_active = 1"
        ).fetchone()[0]
    )
    return {
        "quick_check": quick_check,
        "table_counts": counts,
        "active_opponent_row_count": active_count,
        "active_system_user_ids": system_ids,
        "non_system_opponent_row_count": non_system_count,
        "invalid_opponent_unit_ids": invalid_ids,
    }


def _fresh_verification(
    connection: sqlite3.Connection,
    canonical_ids: set[str],
    payloads: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Verify the replacement contains exactly the intended fresh dataset."""

    expected_by_user = {int(payload["user_id"]): payload for payload in payloads}
    expected_ids = sorted(expected_by_user)
    inventory = _inventory(connection, canonical_ids)
    rows = connection.execute(
        """
        SELECT user_id, nickname, team_json, wins, losses, level, is_active
        FROM opponent_teams
        ORDER BY user_id
        """
    ).fetchall()
    row_ids = [int(row[0]) for row in rows]
    mismatches: list[dict[str, Any]] = []
    for row in rows:
        user_id = int(row[0])
        expected = expected_by_user.get(user_id)
        expected_team = _canonical_team_json(expected) if expected else None
        if (
            expected is None
            or row[1] != expected["nickname"]
            or row[2] != expected_team
            or int(row[3]) != int(expected["wins"])
            or int(row[4]) != int(expected["losses"])
            or int(row[5]) != int(expected["level"])
            or int(row[6]) != 1
        ):
            if len(mismatches) < 20:
                mismatches.append({"user_id": user_id})

    table_counts = inventory["table_counts"]
    checks = {
        "quick_check_ok": inventory["quick_check"] == "ok",
        "required_tables_present": True,
        "players_empty": table_counts["players"] == 0,
        "leaderboard_empty": table_counts["leaderboard"] == 0,
        "player_action_results_empty": table_counts["player_action_results"] == 0,
        "opponent_row_count_exact": table_counts["opponent_teams"] == len(expected_ids),
        "active_opponent_row_count_exact": inventory["active_opponent_row_count"] == len(expected_ids),
        "active_system_user_ids_match": inventory["active_system_user_ids"] == expected_ids,
        "no_non_system_opponents": inventory["non_system_opponent_row_count"] == 0,
        "no_invalid_canonical_unit_ids": not inventory["invalid_opponent_unit_ids"],
        "snapshot_rows_match_canonical_payloads": not mismatches and row_ids == expected_ids,
    }
    verification = {
        "checks": checks,
        "all_passed": all(checks.values()),
        "table_counts": table_counts,
        "active_system_user_ids": inventory["active_system_user_ids"],
        "invalid_opponent_unit_ids": inventory["invalid_opponent_unit_ids"],
        "snapshot_mismatches": mismatches,
    }
    if not verification["all_passed"]:
        failed = [name for name, passed in checks.items() if not passed]
        raise ResetError(f"Fresh database verification failed: {failed}")
    return verification


def _sidecar_paths(database: Path) -> list[Path]:
    return [Path(f"{database}{suffix}") for suffix in SIDECAR_SUFFIXES]


def _backup_database(source: Path, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ResetError(f"Refusing to overwrite existing backup: {destination}")
    source_connection = sqlite3.connect(str(source))
    backup_connection = sqlite3.connect(str(destination))
    try:
        source_connection.backup(backup_connection)
        backup_connection.commit()
    finally:
        backup_connection.close()
        source_connection.close()

    verification_connection = sqlite3.connect(str(destination))
    try:
        quick_check = _quick_check(verification_connection)
    finally:
        verification_connection.close()
    if quick_check != "ok":
        raise ResetError(f"Backup quick_check failed: {quick_check}")
    return {
        "path": str(destination),
        "sha256": _sha256_file(destination),
        "quick_check": quick_check,
    }


def _initialize_staging(path: Path, payloads: Sequence[Mapping[str, Any]]) -> None:
    asyncio.run(DatabaseManager(str(path)).initialize())
    connection = sqlite3.connect(str(path))
    try:
        connection.execute("BEGIN IMMEDIATE")
        for payload in payloads:
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
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _archive_sidecars(database: Path, backup_path: Path) -> list[dict[str, str]]:
    archived: list[dict[str, str]] = []
    for sidecar in _sidecar_paths(database):
        if not sidecar.exists():
            continue
        suffix = sidecar.name[len(database.name):]
        destination = backup_path.with_name(backup_path.name + suffix)
        if destination.exists():
            raise ResetError(f"Refusing to overwrite archived sidecar: {destination}")
        os.replace(sidecar, destination)
        archived.append({"source": str(sidecar), "path": str(destination)})
    return archived


def _restore_archived_sidecars(archived: Sequence[Mapping[str, str]]) -> None:
    for entry in archived:
        source = Path(entry["source"])
        archived_path = Path(entry["path"])
        if archived_path.exists() and not source.exists():
            os.replace(archived_path, source)


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _make_report(
    *,
    status: str,
    database: Path,
    units_path: Path,
    units: Sequence[Mapping[str, Any]],
    seed: int,
    approved_revision: str | None,
    before: Mapping[str, Any],
    payloads: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    canonical_ids = sorted(str(unit["id"]) for unit in units)
    expected_ids = [int(payload["user_id"]) for payload in payloads]
    return {
        "migration": MIGRATION_NAME,
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": str(database),
        "approved_revision": approved_revision,
        "canonical_source": {
            "path": str(units_path),
            "sha256": _sha256_file(units_path),
            "unit_count": len(units),
            "unit_ids": canonical_ids,
            "unit_ids_digest": _json_digest(canonical_ids),
        },
        "encounter_source": {
            "definition_count": len(SYSTEM_ENCOUNTER_DEFINITIONS),
            "seed": seed,
            "system_user_ids": expected_ids,
        },
        "before": dict(before),
    }


def reset_database(
    db_path: Path,
    units_path: Path,
    *,
    seed: int = DEFAULT_ENCOUNTER_SEED,
    apply: bool = False,
    approved_revision: str | None = None,
    confirm: bool = False,
    backup_dir: Path | None = None,
) -> dict[str, Any]:
    """Audit or perform the WFT-169 full database reset."""

    db_path = Path(db_path).resolve()
    units_path = Path(units_path).resolve()
    if not db_path.is_file():
        raise ResetError(f"Database not found: {db_path}")
    if not units_path.is_file():
        raise ResetError(f"Canonical units source not found: {units_path}")
    if apply:
        if not confirm:
            raise ResetError("Apply mode requires --confirm-wft-169")
        if not approved_revision or not re.fullmatch(r"[0-9a-fA-F]{7,40}", approved_revision):
            raise ResetError(
                "Apply mode requires --approved-revision with a git SHA (7-40 hex characters)"
            )

    try:
        units = load_canonical_units(units_path)
    except OpponentMigrationError as exc:
        raise ResetError(str(exc)) from exc

    canonical_ids = {str(unit["id"]) for unit in units}
    payloads = build_system_opponent_payloads(units, seed=seed)
    source_connection = sqlite3.connect(str(db_path))
    try:
        source_connection.execute("PRAGMA foreign_keys = ON")
        before = _inventory(source_connection, canonical_ids)
    finally:
        source_connection.close()

    report = _make_report(
        status="dry_run" if not apply else "pending",
        database=db_path,
        units_path=units_path,
        units=units,
        seed=seed,
        approved_revision=approved_revision,
        before=before,
        payloads=payloads,
    )
    report["planned_reset"] = {
        "removed_rows": dict(before["table_counts"]),
        "replacement_table_counts": {
            "players": 0,
            "leaderboard": 0,
            "player_action_results": 0,
            "opponent_teams": len(payloads),
        },
        "replacement_active_system_user_ids": [int(payload["user_id"]) for payload in payloads],
    }
    if not apply:
        return report

    if backup_dir is None:
        backup_dir = db_path.parent / "migration-backups"
    backup_dir = Path(backup_dir).resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    run_stamp = _timestamp()
    backup_path = backup_dir / f"wft-169-pre-reset-{run_stamp}.db"
    staging_path = db_path.parent / f".{db_path.name}.wft169-staging-{run_stamp}-{uuid.uuid4().hex}.db"
    if staging_path.exists():
        raise ResetError(f"Refusing to overwrite staging database: {staging_path}")

    swapped = False
    archived_sidecars: list[dict[str, str]] = []
    try:
        _initialize_staging(staging_path, payloads)
        staging_connection = sqlite3.connect(str(staging_path))
        try:
            staging_verification = _fresh_verification(staging_connection, canonical_ids, payloads)
        finally:
            staging_connection.close()

        backup = _backup_database(db_path, backup_path)
        archived_sidecars = _archive_sidecars(db_path, backup_path)
        staging_sidecars = [path for path in _sidecar_paths(staging_path) if path.exists()]
        if staging_sidecars:
            raise ResetError(f"Staging database has unexpected sidecars: {staging_sidecars}")

        os.replace(staging_path, db_path)
        swapped = True
        final_connection = sqlite3.connect(str(db_path))
        try:
            final_verification = _fresh_verification(final_connection, canonical_ids, payloads)
        finally:
            final_connection.close()

        report.update(
            {
                "status": "applied",
                "backup": {
                    **backup,
                    "archived_sidecars": archived_sidecars,
                },
                "staging": {
                    "path": str(staging_path),
                    "verification": staging_verification,
                },
                "after": final_verification,
                "changes": {
                    "removed_rows": dict(before["table_counts"]),
                    "inserted_system_rows": len(payloads),
                    "historical_opponent_rows_removed": before["table_counts"]["opponent_teams"],
                },
                "verification": {
                    "backup_sha256_verified": _sha256_file(backup_path) == backup["sha256"],
                    "backup_quick_check_ok": backup["quick_check"] == "ok",
                    "staging_database_valid": staging_verification["all_passed"],
                    "final_database_valid": final_verification["all_passed"],
                    "legacy_player_state_retained": False,
                    "legacy_item_ids_mapped": False,
                    "rollback_performed": False,
                },
            }
        )
        return report
    except Exception as exc:
        if swapped:
            rollback_path = db_path.parent / f".{db_path.name}.wft169-rollback-{run_stamp}-{uuid.uuid4().hex}.db"
            shutil.copy2(backup_path, rollback_path)
            os.replace(rollback_path, db_path)
        elif archived_sidecars:
            _restore_archived_sidecars(archived_sidecars)
        if staging_path.exists():
            staging_path.unlink()
        if isinstance(exc, ResetError):
            raise
        raise ResetError(f"WFT-169 reset aborted: {exc}") from exc


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--units", type=Path, default=DEFAULT_UNITS_PATH)
    parser.add_argument("--seed", type=int, default=DEFAULT_ENCOUNTER_SEED)
    parser.add_argument("--apply", action="store_true", help="Create and atomically install the fresh database")
    parser.add_argument("--confirm-wft-169", action="store_true", help="Required with --apply")
    parser.add_argument("--approved-revision", help="Approved git SHA required with --apply")
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--report", type=Path, help="Write the JSON report to this path")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
        report = reset_database(
            args.db,
            args.units,
            seed=args.seed,
            apply=args.apply,
            approved_revision=args.approved_revision,
            confirm=args.confirm_wft_169,
            backup_dir=args.backup_dir,
        )
    except (ResetError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.report:
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
