import { emptyBoard, isAugmentRound, type RunState } from '@reforged/schema';
import { getUnitList } from '@reforged/content-data';
import type { Db } from '../db/client.js';
import { getCurrentActiveRun, getRunById, insertRun, newRunId, updateRun } from '../db/runRepository.js';
import { roundIncome, rollShopOffers, STARTING_GOLD } from './economyService.js';

export class RunNotFoundError extends Error {}
export class RunForbiddenError extends Error {}

export function createRun(db: Db, userId: string): RunState {
  const run: RunState = {
    runId: newRunId(),
    userId,
    status: 'active',
    wins: 0,
    losses: 0,
    roundNumber: 1,
    gold: STARTING_GOLD,
    level: 1,
    units: [],
    board: emptyBoard(),
    augmentsPicked: [],
    augmentPending: false,
    shopOffers: rollShopOffers(1, getUnitList()),
    shopLocked: false,
  };
  insertRun(db, run);
  return run;
}

export function getCurrentRun(db: Db, userId: string): RunState | null {
  return getCurrentActiveRun(db, userId);
}

export function requireOwnedRun(db: Db, userId: string, runId: string): RunState {
  const run = getRunById(db, runId);
  if (!run) throw new RunNotFoundError(runId);
  if (run.userId !== userId) throw new RunForbiddenError(runId);
  return run;
}

export function persistRun(db: Db, run: RunState): RunState {
  updateRun(db, run);
  return run;
}

/**
 * Advances the round counter, pays round income, and flags an augment pick
 * when the new round lands on an augment round (every 2 rounds — plan
 * decision #7). Called by the combat orchestrator after a fight resolves
 * (Phase 5); exposed here too so the economy loop is independently testable.
 */
export function advanceRound(run: RunState): RunState {
  const roundNumber = run.roundNumber + 1;
  const gold = run.gold + roundIncome(run.gold);
  const augmentPending = run.augmentPending || isAugmentRound(roundNumber);
  return { ...run, roundNumber, gold, augmentPending };
}

export function applyMatchResult(run: RunState, won: boolean): RunState {
  const wins = run.wins + (won ? 1 : 0);
  const losses = run.losses + (won ? 0 : 1);
  const status = wins >= 10 ? 'won' : losses >= 5 ? 'lost' : 'active';
  return { ...run, wins, losses, status };
}
