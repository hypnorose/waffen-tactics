import { eq, ne } from 'drizzle-orm';
import type { BoardPosition } from '@reforged/schema';
import type { Db } from './client.js';
import { runSnapshots } from './schema.js';

export interface SnapshotUnit {
  position: BoardPosition;
  unitId: string;
}

export interface RunSnapshot {
  userId: string;
  username: string;
  elo: number;
  roundNumber: number;
  units: SnapshotUnit[];
  augmentsPicked: string[];
}

/**
 * Upserts one snapshot per (userId, roundNumber), overwriting any earlier
 * attempt at the same round — used by matchmaking to seat other players'
 * boards as async PvP opponents (see matchmakingService).
 */
export function saveSnapshot(db: Db, snapshot: RunSnapshot): void {
  const id = `${snapshot.userId}:${snapshot.roundNumber}`;
  const row = {
    id,
    userId: snapshot.userId,
    username: snapshot.username,
    elo: snapshot.elo,
    roundNumber: snapshot.roundNumber,
    unitsJson: JSON.stringify(snapshot.units),
    augmentsPickedJson: JSON.stringify(snapshot.augmentsPicked),
    createdAt: Date.now(),
  };

  const existing = db.select().from(runSnapshots).where(eq(runSnapshots.id, id)).get();
  if (existing) {
    db.update(runSnapshots).set(row).where(eq(runSnapshots.id, id)).run();
  } else {
    db.insert(runSnapshots).values(row).run();
  }
}

/** All other players' snapshots, for matchmaking to pick the closest round/elo match from. */
export function listOtherSnapshots(db: Db, excludeUserId: string): RunSnapshot[] {
  return db
    .select()
    .from(runSnapshots)
    .where(ne(runSnapshots.userId, excludeUserId))
    .all()
    .map((row) => ({
      userId: row.userId,
      username: row.username,
      elo: row.elo,
      roundNumber: row.roundNumber,
      units: JSON.parse(row.unitsJson),
      augmentsPicked: JSON.parse(row.augmentsPickedJson),
    }));
}
