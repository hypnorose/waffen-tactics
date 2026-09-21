import { eq } from 'drizzle-orm';
import type { CombatLog, Side } from '@reforged/schema';
import type { Db } from './client.js';
import { combatLogs } from './schema.js';

export function insertCombatLog(db: Db, runId: string, log: CombatLog, winner: Side): void {
  db.insert(combatLogs)
    .values({
      id: log.combatId,
      runId,
      seed: log.seed,
      eventsJson: JSON.stringify(log.events),
      winner,
      createdAt: Date.now(),
    })
    .run();
}

export function getCombatLogById(db: Db, combatId: string): CombatLog | null {
  const row = db.select().from(combatLogs).where(eq(combatLogs.id, combatId)).get();
  if (!row) return null;
  return { combatId: row.id, seed: row.seed, events: JSON.parse(row.eventsJson) };
}

export function getCombatLogRunId(db: Db, combatId: string): string | null {
  const row = db.select({ runId: combatLogs.runId }).from(combatLogs).where(eq(combatLogs.id, combatId)).get();
  return row?.runId ?? null;
}
