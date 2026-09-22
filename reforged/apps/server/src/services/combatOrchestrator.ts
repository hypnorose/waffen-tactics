import { randomUUID } from 'node:crypto';
import { runCombat, type CombatParticipantInput } from '@reforged/combat-engine';
import { augmentDefs, getUnitDefs } from '@reforged/content-data';
import type { AbilityEffect, CombatLog, RunState, Side, UnitDef } from '@reforged/schema';
import { STARTING_ELO, unitHpContribution } from '@reforged/schema';
import { discordAvatarUrl } from '../auth/discord.js';
import type { Db } from '../db/client.js';
import { insertCombatLog } from '../db/combatLogRepository.js';
import { saveSnapshot } from '../db/runSnapshotRepository.js';
import { findUserById, updateElo } from '../db/userRepository.js';
import { findOpponent } from './matchmakingService.js';
import { runEloDelta } from './rankService.js';
import { advanceRound, applyMatchResult, persistRun } from './runService.js';

function computeTeamHpMax(unitIds: string[], unitDefs: Record<string, UnitDef>): number {
  return unitIds.reduce((sum, unitId) => sum + unitHpContribution(unitDefs[unitId]?.cost ?? 1), 0);
}

function toAugmentEffects(augmentIds: string[]): Array<{ effect: AbilityEffect; tagFilter?: string[] }> {
  return augmentIds
    .map((id) => augmentDefs.find((a) => a.id === id))
    .filter((a): a is NonNullable<typeof a> => !!a)
    .flatMap((a) => a.effects.map((effect) => ({ effect, tagFilter: a.tagFilter })));
}

export interface CombatResult {
  run: RunState;
  combatLog: CombatLog;
  winner: Side;
  opponentName: string;
  opponentAvatarUrl: string | null;
}

export class RunNotActiveError extends Error {}
export class AugmentPendingError extends Error {}
export class EmptyBoardError extends Error {}

/**
 * Orchestrates one fight: seats the run's board against the closest-matching
 * opponent (another player's snapshot at the same round/elo, or the PvE bot
 * ladder as a fallback — see matchmakingService), runs the deterministic
 * engine, then applies the result to the run (win/loss -> status, round
 * advance -> income/augment gating) and persists both. Returns the full
 * event log as one JSON payload — combat is fully computed up front, so the
 * client paces replay locally from each event's `simTime` rather than the
 * server streaming it live (a deliberate simplification of the plan's "SSE
 * streaming" decision #11: there is no real-time process on the server to
 * stream from).
 */
export function runCombatForRun(db: Db, run: RunState): CombatResult {
  if (run.status !== 'active') throw new RunNotActiveError();
  if (run.augmentPending) throw new AugmentPendingError();

  const unitDefs = getUnitDefs();

  const playerParticipants: CombatParticipantInput[] = run.board
    .filter((slot) => slot.unitInstanceId !== null)
    .map((slot) => {
      const instance = run.units.find((u) => u.instanceId === slot.unitInstanceId)!;
      return { instanceId: instance.instanceId, unitId: instance.unitId, position: slot.position };
    });

  if (playerParticipants.length === 0) throw new EmptyBoardError();

  const user = findUserById(db, run.userId);
  const playerElo = user?.elo ?? STARTING_ELO;

  // Snapshot this player's board at this round *before* the fight, so other
  // players' matchmaking can seat them as an async PvP opponent — see
  // matchmakingService.
  saveSnapshot(db, {
    userId: run.userId,
    username: user?.username ?? 'Unknown',
    avatarUrl: user ? discordAvatarUrl({ id: user.id, avatarHash: user.avatarHash }) : null,
    elo: playerElo,
    roundNumber: run.roundNumber,
    units: playerParticipants.map((p) => ({ position: p.position, unitId: p.unitId })),
    augmentsPicked: run.augmentsPicked,
  });

  const opponent = findOpponent(db, run, playerElo);
  const enemyParticipants: CombatParticipantInput[] = opponent.units.map((u, i) => ({
    instanceId: `enemy:${i}`,
    unitId: u.unitId,
    position: u.position,
  }));

  const combatLog = runCombat({
    combatId: randomUUID(),
    seed: Math.floor(Math.random() * 2 ** 31),
    player: {
      side: 'player',
      units: playerParticipants,
      hpMax: computeTeamHpMax(playerParticipants.map((p) => p.unitId), unitDefs),
      augmentEffects: toAugmentEffects(run.augmentsPicked),
    },
    enemy: {
      side: 'enemy',
      units: enemyParticipants,
      hpMax: computeTeamHpMax(enemyParticipants.map((p) => p.unitId), unitDefs),
      augmentEffects: toAugmentEffects(opponent.augmentsPicked),
    },
    unitDefs,
  });

  const victoryEvent = combatLog.events.find((e) => e.type === 'victory');
  const winner: Side = victoryEvent?.type === 'victory' ? victoryEvent.winner : 'enemy';

  const afterMatch = applyMatchResult(run, winner === 'player');
  const finalRun = afterMatch.status === 'active' ? advanceRound(afterMatch) : afterMatch;

  persistRun(db, finalRun);
  insertCombatLog(db, run.runId, combatLog, winner);

  // Elo only moves once the run actually concludes (10 wins or 5 losses),
  // not after every individual match — see rankService.
  if (finalRun.status !== 'active' && user) {
    updateElo(db, user.id, user.elo + runEloDelta(finalRun.status, finalRun.wins));
  }

  return { run: finalRun, combatLog, winner, opponentName: opponent.name, opponentAvatarUrl: opponent.avatarUrl };
}
