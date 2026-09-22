import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from './schema.js';

const DDL = `
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL,
  avatar_hash TEXT,
  elo INTEGER NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  status TEXT NOT NULL,
  wins INTEGER NOT NULL,
  losses INTEGER NOT NULL,
  round_number INTEGER NOT NULL,
  gold INTEGER NOT NULL,
  level INTEGER NOT NULL,
  units_json TEXT NOT NULL,
  board_json TEXT NOT NULL,
  augments_picked_json TEXT NOT NULL,
  augment_pending INTEGER NOT NULL,
  augment_offers_json TEXT,
  shop_offers_json TEXT NOT NULL,
  shop_locked INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS run_snapshots (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  username TEXT NOT NULL,
  avatar_url TEXT,
  elo INTEGER NOT NULL,
  round_number INTEGER NOT NULL,
  units_json TEXT NOT NULL,
  augments_picked_json TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS combat_logs (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  seed INTEGER NOT NULL,
  events_json TEXT NOT NULL,
  winner TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_user_id ON runs (user_id);
CREATE INDEX IF NOT EXISTS idx_combat_logs_run_id ON combat_logs (run_id);
CREATE INDEX IF NOT EXISTS idx_run_snapshots_user_id ON run_snapshots (user_id);
`;

export type Db = ReturnType<typeof createDb>;

export function createDb(fileName: string) {
  const sqlite = new Database(fileName);
  sqlite.pragma('journal_mode = WAL');
  sqlite.exec(DDL);
  // Existing deployments predate avatar_url. Keep old snapshots usable and
  // add the nullable column in place instead of requiring a database reset.
  const snapshotColumns = sqlite.pragma('table_info(run_snapshots)') as Array<{ name: string }>;
  if (!snapshotColumns.some((column) => column.name === 'avatar_url')) {
    sqlite.exec('ALTER TABLE run_snapshots ADD COLUMN avatar_url TEXT');
  }
  return drizzle(sqlite, { schema });
}
