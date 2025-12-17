#!/usr/bin/env python3
"""
Normalize system opponent rows in the database.

This script makes a backup of the DB and ensures that for each system
opponent (user_id <= 100) exactly one row is marked `is_active = 1` (the
most-recent row), and all other rows for that user are set to `is_active = 0`.

Usage:
  python3 scripts/normalize_system_opponents.py [--db /path/to/waffen_tactics_game.db]

Be careful: a backup is created next to the DB file before any changes.
"""
import sqlite3
import shutil
import time
import argparse
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', help='Path to SQLite DB', default=None)
    args = ap.parse_args()

    # Default DB path relative to repo root if not provided
    if args.db:
        db_path = args.db
    else:
        db_path = os.path.join(os.getcwd(), 'waffen-tactics', 'waffen_tactics_game.db')

    if not os.path.exists(db_path):
        print(f"ERROR: DB not found at {db_path}")
        sys.exit(2)

    # Backup DB
    ts = int(time.time())
    backup_path = f"{db_path}.backup.{ts}"
    print(f"Backing up DB: {db_path} -> {backup_path}")
    shutil.copy2(db_path, backup_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Ensure table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='opponent_teams'")
    if not cur.fetchone():
        print("ERROR: Table 'opponent_teams' not found in DB")
        conn.close()
        sys.exit(3)

    # Inspect columns
    cur.execute("PRAGMA table_info('opponent_teams')")
    cols = [r[1] for r in cur.fetchall()]
    print(f"opponent_teams columns: {cols}")

    # Count system rows
    cur.execute("SELECT COUNT(*) FROM opponent_teams WHERE user_id <= 100")
    total_system = cur.fetchone()[0]
    print(f"Total system opponent rows (user_id <= 100): {total_system}")

    if total_system == 0:
        print("No system opponent rows found; nothing to do.")
        conn.close()
        return

    try:
        conn.execute('BEGIN')

        # Deactivate all system rows first
        cur.execute("UPDATE opponent_teams SET is_active = 0 WHERE user_id <= 100")

        # Find distinct system user_ids
        cur.execute("SELECT DISTINCT user_id FROM opponent_teams WHERE user_id <= 100")
        user_ids = [r[0] for r in cur.fetchall()]

        # Determine ordering column preference
        has_created_at = 'created_at' in cols
        has_id = 'id' in cols

        activated = 0
        for uid in user_ids:
            if has_created_at:
                cur.execute("SELECT rowid FROM opponent_teams WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (uid,))
                row = cur.fetchone()
                if row:
                    rowid = row[0]
                    cur.execute("UPDATE opponent_teams SET is_active = 1 WHERE rowid = ?", (rowid,))
                    activated += 1
            elif has_id:
                cur.execute("SELECT id FROM opponent_teams WHERE user_id = ? ORDER BY id DESC LIMIT 1", (uid,))
                row = cur.fetchone()
                if row:
                    rid = row[0]
                    cur.execute("UPDATE opponent_teams SET is_active = 1 WHERE id = ?", (rid,))
                    activated += 1
            else:
                # Fall back to rowid ordering
                cur.execute("SELECT rowid FROM opponent_teams WHERE user_id = ? ORDER BY rowid DESC LIMIT 1", (uid,))
                row = cur.fetchone()
                if row:
                    rowid = row[0]
                    cur.execute("UPDATE opponent_teams SET is_active = 1 WHERE rowid = ?", (rowid,))
                    activated += 1

        conn.commit()
        print(f"Activated {activated} system opponent rows (one per system user_id)")

        # Summary of active rows
        cur.execute("SELECT user_id, COUNT(*) as cnt FROM opponent_teams WHERE user_id <= 100 AND is_active = 1 GROUP BY user_id")
        rows = cur.fetchall()
        print(f"Active rows per system user (sample): {rows[:20]}")

    except Exception as e:
        conn.rollback()
        print(f"ERROR during normalization: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
