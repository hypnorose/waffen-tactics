import { z } from 'zod';
import { BoardSchema } from './board.js';
import { UnitInstanceSchema, type UnitInstance } from './unit.js';

export const AugmentTierSchema = z.enum(['bronze', 'silver', 'gold']);
export type AugmentTier = z.infer<typeof AugmentTierSchema>;

export const RunStatusSchema = z.enum(['active', 'won', 'lost']);
export type RunStatus = z.infer<typeof RunStatusSchema>;

// A run ends at 10 wins or 5 losses — see plan decision #9.
//
// `units` holds every UnitInstance the run owns, whether benched or placed;
// `board` only references instanceIds into it. "Benched" is derived (an
// instance not referenced by any board slot) rather than tracked as a
// separate list, so there's exactly one place instance data can live.
export const RunStateSchema = z.object({
  runId: z.string(),
  userId: z.string(),
  status: RunStatusSchema,
  wins: z.number().int().min(0).max(10),
  losses: z.number().int().min(0).max(5),
  roundNumber: z.number().int().min(1),
  gold: z.number().int().min(0),
  level: z.number().int().min(1).max(5),
  units: z.array(UnitInstanceSchema).max(18),
  board: BoardSchema,
  augmentsPicked: z.array(z.string()),
  augmentPending: z.boolean(),
  augmentOffers: z.array(z.string()).length(3).optional(),
  shopOffers: z.array(z.string().nullable()).length(5),
  shopLocked: z.boolean(),
});
export type RunState = z.infer<typeof RunStateSchema>;

export function getBoardUnitIds(run: Pick<RunState, 'board'>): Set<string> {
  return new Set(run.board.map((slot) => slot.unitInstanceId).filter((id): id is string => id !== null));
}

export function getBenchedUnits(run: Pick<RunState, 'units' | 'board'>): UnitInstance[] {
  const onBoard = getBoardUnitIds(run);
  return run.units.filter((u) => !onBoard.has(u.instanceId));
}

// Augment tier is keyed to pick index (1-3 bronze, 4-6 silver, 7+ gold),
// picks occur every 2 rounds starting round 2 — see plan decision #7.
export function tierForPickIndex(pickIndex: number): AugmentTier {
  if (pickIndex <= 3) return 'bronze';
  if (pickIndex <= 6) return 'silver';
  return 'gold';
}

export function isAugmentRound(roundNumber: number): boolean {
  return roundNumber >= 2 && roundNumber % 2 === 0;
}
