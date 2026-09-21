import { findClosestBot, type BotProfile } from '@reforged/content-data';
import type { BoardPosition, RunState } from '@reforged/schema';
import type { Db } from '../db/client.js';
import { listOtherSnapshots, type RunSnapshot } from '../db/runSnapshotRepository.js';
import { autoPlaceOnBoard } from './boardService.js';

export interface OpponentUnit {
  unitId: string;
  position: BoardPosition;
}

export interface Opponent {
  name: string;
  units: OpponentUnit[];
  augmentsPicked: string[];
}

/**
 * Prefers a snapshot of another real player's board at the same round and
 * with as close a ranking as possible, so PvP starts from fight 1; falls
 * back to the PvE bot ladder (plan decision #8) once no snapshot exists yet
 * (e.g. the very first run on a fresh server).
 */
export function findOpponent(db: Db, run: RunState, playerElo: number): Opponent {
  const snapshot = findClosestSnapshot(db, run.userId, run.roundNumber, playerElo);
  if (snapshot) return { name: snapshot.username, units: snapshot.units, augmentsPicked: snapshot.augmentsPicked };
  return botToOpponent(findClosestBot(run.wins));
}

function findClosestSnapshot(db: Db, excludeUserId: string, roundNumber: number, elo: number): RunSnapshot | null {
  const candidates = listOtherSnapshots(db, excludeUserId);
  if (candidates.length === 0) return null;
  return candidates.reduce((best, candidate) =>
    isCloserMatch(candidate, best, roundNumber, elo) ? candidate : best,
  );
}

/** Same round number wins outright; ties (and only ties) break on closest elo. */
function isCloserMatch(candidate: RunSnapshot, current: RunSnapshot, roundNumber: number, elo: number): boolean {
  const roundDiff = Math.abs(candidate.roundNumber - roundNumber);
  const currentRoundDiff = Math.abs(current.roundNumber - roundNumber);
  if (roundDiff !== currentRoundDiff) return roundDiff < currentRoundDiff;
  return Math.abs(candidate.elo - elo) < Math.abs(current.elo - elo);
}

function botToOpponent(bot: BotProfile): Opponent {
  const board = autoPlaceOnBoard(bot.unitIds.map((_, i) => `bot:${i}`));
  const units = board
    .filter((slot) => slot.unitInstanceId !== null)
    .map((slot, i) => ({ unitId: bot.unitIds[i], position: slot.position }));
  return { name: bot.name, units, augmentsPicked: [] };
}
