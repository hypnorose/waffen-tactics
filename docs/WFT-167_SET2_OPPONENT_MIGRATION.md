# WFT-167 — Set 2 opponent-pool migration

## Source of truth

- Database: `waffen-tactics/waffen_tactics_game.db`
- Canonical unit source: `waffen-tactics/units.json`
- Encounter definitions: `waffen-tactics/src/waffen_tactics/services/encounter_definitions.py`
- Migration: `scripts/rebuild_set2_opponents.py`
- Scope: `opponent_teams` only. `players`, `leaderboard`, and
  `player_action_results` are protected and must remain unchanged.

The migration keeps the existing system-opponent progression ladder (38
profiles) and regenerates only their persisted unit IDs from the active Set 2
unit source. The generator is deterministic with seed `167` and never reads
the archived roster.

## Preflight and dry-run

Run from the repository root and record the approved commit SHA:

```bash
git rev-parse HEAD
python3 scripts/rebuild_set2_opponents.py \
  --db waffen-tactics/waffen_tactics_game.db \
  --units waffen-tactics/units.json
```

Dry-run must report `status: "dry_run"`, `canonical_source.unit_count: 32`,
`encounter_source.definition_count: 38`, and the complete pre-migration
active/invalid row counts. It does not create a backup and does not mutate the
database.

Before apply, confirm that the revision contains the canonical Set 2 dataset,
the shared encounter definitions, and the migration tests. Do not use a
working-tree-only revision for production.

## Controlled production apply

The service must be stopped during the short write window so no combat or
player-action writer can race the migration:

```bash
cd /home/ubuntu/waffen-tactics-game
./stop-all.sh
git rev-parse HEAD
python3 scripts/rebuild_set2_opponents.py \
  --db waffen-tactics/waffen_tactics_game.db \
  --units waffen-tactics/units.json \
  --seed 167 \
  --apply \
  --confirm-wft-167 \
  --approved-revision <approved-git-sha> \
  --backup-dir waffen-tactics/migration-backups \
  --report waffen-tactics/migration-backups/wft-167-report.json
./start-all.sh
./status.sh
```

Apply mode refuses to run without both `--confirm-wft-167` and a full git SHA.
It creates a SQLite online-backup before `BEGIN IMMEDIATE`, then:

1. deactivates active stale snapshots, including removed legacy IDs;
2. leaves player/account tables unchanged;
3. updates or inserts the 38 deterministic system profiles;
4. verifies zero active opponent rows with invalid Set 2 data; and
5. verifies that the active system user IDs exactly match the encounter
   definitions.

The command prints and records the backup path, SHA-256, before/after counts,
invalid-ID counts, affected row counts, approved revision, source hash, and
protected-table verification. Keep the backup and report together for
rollback/audit; never overwrite an existing backup.

## Rollback

Do not delete the pre-cutover backup. If the post-migration checks fail, the
transaction rolls back automatically. If a committed restore is required,
stop the services, preserve the current database as a second backup, restore
the recorded pre-cutover SQLite snapshot to the runtime path, then restart and
run the read-only audit again. A restore must not be performed over a running
database.

## Post-migration verification

Automated:

```bash
python3 scripts/rebuild_set2_opponents.py \
  --db waffen-tactics/waffen_tactics_game.db \
  --units waffen-tactics/units.json
```

Expected: `status: "dry_run"`, `before.active_invalid_row_count: 0`, and 38
active system user IDs. Re-running apply with the same revision/seed must
report zero new or updated system rows (apart from creating a fresh backup).

Runtime:

- `./status.sh` shows backend, frontend, and managed Caddy healthy.
- Start combat from the affected account without changing its board.
- Confirm a successful combat completion in `waffen-tactics-web/backend/api.log`.
- Confirm no new `invalid_combat_input` caused by a stale opponent ID.
- Confirm the player state/progression remains intact.
- Capture timestamp, account/user identifier, selected opponent nickname, and
  the migration report path in the WFT-167 Plane comment.

The frontend SSE error classification remains WFT-166, and fail-closed
handling of any invalid snapshot remains WFT-168. This migration does not add
legacy ID mappings or an automatic fallback opponent.
