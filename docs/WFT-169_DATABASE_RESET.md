# WFT-169 production database reset

WFT-169 replaces the active SQLite database with a newly initialized database.
It intentionally removes every player save, leaderboard row, idempotency/action
result, and historical opponent snapshot. It does not map or mutate legacy item
IDs. The replacement contains only the canonical Set 2 system encounters.

## Safe execution

Run from the deployed repository after stopping the application processes:

```bash
cd /home/ubuntu/waffen-tactics-game
./stop-all.sh
git rev-parse HEAD
PYTHONPATH=waffen-tactics/src waffen-tactics-web/backend/venv/bin/python \
  scripts/reset_production_database.py \
  --apply \
  --confirm-wft-169 \
  --approved-revision <deployed-commit-sha> \
  --report waffen-tactics/migration-backups/wft-169-reset-report-<utc-stamp>.json
./start-all.sh
./status.sh
```

`--apply` is never implicit. The command refuses to run without the explicit
WFT-169 confirmation and a 7–40 character git SHA. Before swapping the active
database it:

1. initializes a unique staging database through `DatabaseManager.initialize()`;
2. seeds the 38 deterministic profiles from `build_system_opponent_payloads()`;
3. verifies the staging schema, SQLite `quick_check`, empty player/account
   tables, exact system IDs `1..38`, and canonical unit IDs;
4. creates a verified SQLite backup under `migration-backups/` and records its
   SHA-256 hash;
5. archives any exact target `-wal`, `-shm`, or `-journal` sidecars beside the
   backup;
6. atomically replaces the active database and verifies it again.

If post-swap verification fails, the verified backup is restored before the
command exits with an error. The backup is never deleted or overwritten.

## Verification acceptance

The JSON report must show:

- `status: "applied"`;
- a verified backup path and SHA-256 hash;
- `before.table_counts` containing the removed rows;
- replacement counts of `players=0`, `leaderboard=0`,
  `player_action_results=0`, and `opponent_teams=38`;
- active system user IDs exactly `1..38`;
- `verification.final_database_valid: true`.

After the services are healthy, log in with a fresh player account and run one
combat manually. Record the result in Plane; automated schema/count checks do
not replace this runtime acceptance.
