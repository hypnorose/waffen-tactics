import { randomUUID } from 'node:crypto';
import { runCombat, type CombatParticipantInput } from '@reforged/combat-engine';
import { getUnitDefs } from '@reforged/content-data';
import type { CombatLog, RunState, Side, UnitDef } from '@reforged/schema';
import type { Db } from '../db/client.js';
import { insertCombatLog } from '../db/combatLogRepository.js';
import { autoPlaceOnBoard } from './boardService.js';
import { findOpponent } from './matchmakingService.js';
import { advanceRound, applyMatchResult, persistRun } from './runService.js';

// Placeholder balance (like economyService's odds/xp tables): each unit on
// the board contributes a flat + cost-scaled slice of its team's shared HP
// pool. Defense (see combat-engine's mitigation formula) is the only stat
// that reduces incoming damage — pool size is purely "how much roster you
// committed to this fight".
const BASE_UNIT_HP = 50;
const HP_PER_COST = 20;

function computeTeamHpMax(unitIds: string[], unitDefs: Record<string, UnitDef>): number {
  return unitIds.reduce((sum, unitId) => sum + BASE_UNIT_HP + (unitDefs[unitId]?.cost ?? 1) * HP_PER_COST, 0);
}

export interface CombatResult {
  run: RunState;
  combatLog: CombatLog;
  winner: Side;
}

export class RunNotActiveError extends Error {}
export class AugmentPendingError extends Error {}
export class EmptyBoardError extends Error {}

/**
 * Orchestrates one PvE fight: seats the run's board against the closest bot
 * ladder opponent, runs the deterministic engine, then applies the result to
 * the run (win/loss -> status, round advance -> income/augment gating) and
 * persists both. Returns the full event log as one JSON payload — combat is
 * fully computed up front, so the client paces replay locally from each
 * event's `simTime` rather than the server streaming it live (a deliberate
 * simplification of the plan's "SSE streaming" decision #11: there is no
 * real-time process on the server to stream from).
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

  const opponent = findOpponent(run);
  const enemyBoard = autoPlaceOnBoard(opponent.unitIds.map((_, i) => `bot:${i}`));
  const enemyParticipants: CombatParticipantInput[] = enemyBoard
    .filter((slot) => slot.unitInstanceId !== null)
    .map((slot, i) => ({ instanceId: slot.unitInstanceId!, unitId: opponent.unitIds[i], position: slot.position }));

  const combatLog = runCombat({
    combatId: randomUUID(),
    seed: Math.floor(Math.random() * 2 ** 31),
    player: {
      side: 'player',
      units: playerParticipants,
      hpMax: computeTeamHpMax(playerParticipants.map((p) => p.unitId), unitDefs),
    },
    enemy: {
      side: 'enemy',
      units: enemyParticipants,
      hpMax: computeTeamHpMax(enemyParticipants.map((p) => p.unitId), unitDefs),
    },
    unitDefs,
  });

  const victoryEvent = combatLog.events.find((e) => e.type === 'victory');
  const winner: Side = victoryEvent?.type === 'victory' ? victoryEvent.winner : 'enemy';

  const afterMatch = applyMatchResult(run, winner === 'player');
  const finalRun = afterMatch.status === 'active' ? advanceRound(afterMatch) : afterMatch;

  persistRun(db, finalRun);
  insertCombatLog(db, run.runId, combatLog, winner);

  return { run: finalRun, combatLog, winner };
}
