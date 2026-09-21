import { randomUUID } from 'node:crypto';
import { and, desc, eq } from 'drizzle-orm';
import type { RunState } from '@reforged/schema';
import type { Db } from './client.js';
import { runs } from './schema.js';

type RunRow = typeof runs.$inferSelect;

function rowToRunState(row: RunRow): RunState {
  return {
    runId: row.id,
    userId: row.userId,
    status: row.status as RunState['status'],
    wins: row.wins,
    losses: row.losses,
    roundNumber: row.roundNumber,
    gold: row.gold,
    level: row.level,
    xp: row.xp,
    units: JSON.parse(row.unitsJson),
    board: JSON.parse(row.boardJson),
    augmentsPicked: JSON.parse(row.augmentsPickedJson),
    augmentPending: row.augmentPending === 1,
    augmentOffers: row.augmentOffersJson ? JSON.parse(row.augmentOffersJson) : undefined,
    shopOffers: JSON.parse(row.shopOffersJson),
    shopLocked: row.shopLocked === 1,
  };
}

function runStateToRow(run: RunState) {
  return {
    id: run.runId,
    userId: run.userId,
    status: run.status,
    wins: run.wins,
    losses: run.losses,
    roundNumber: run.roundNumber,
    gold: run.gold,
    level: run.level,
    xp: run.xp,
    unitsJson: JSON.stringify(run.units),
    boardJson: JSON.stringify(run.board),
    augmentsPickedJson: JSON.stringify(run.augmentsPicked),
    augmentPending: run.augmentPending ? 1 : 0,
    augmentOffersJson: run.augmentOffers ? JSON.stringify(run.augmentOffers) : null,
    shopOffersJson: JSON.stringify(run.shopOffers),
    shopLocked: run.shopLocked ? 1 : 0,
  };
}

export function insertRun(db: Db, run: RunState): void {
  const now = Date.now();
  db.insert(runs)
    .values({ ...runStateToRow(run), createdAt: now, updatedAt: now })
    .run();
}

export function updateRun(db: Db, run: RunState): void {
  db.update(runs)
    .set({ ...runStateToRow(run), updatedAt: Date.now() })
    .where(eq(runs.id, run.runId))
    .run();
}

export function getRunById(db: Db, runId: string): RunState | null {
  const row = db.select().from(runs).where(eq(runs.id, runId)).get();
  return row ? rowToRunState(row) : null;
}

export function getCurrentActiveRun(db: Db, userId: string): RunState | null {
  const row = db
    .select()
    .from(runs)
    .where(and(eq(runs.userId, userId), eq(runs.status, 'active')))
    .orderBy(desc(runs.createdAt))
    .get();
  return row ? rowToRunState(row) : null;
}

export function newRunId(): string {
  return randomUUID();
}
