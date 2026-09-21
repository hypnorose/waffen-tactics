import { useMemo } from 'react';
import type { BoardPosition, CombatEvent, Side, UnitCombatState } from '@reforged/schema';

export interface UnitRuntimeSnapshot {
  instanceId: string;
  unitId: string;
  side: Side;
  position: BoardPosition;
  attackIntervalSec: number;
  lastAttackAt: number;
}

export interface RecentAttack {
  instanceId: string;
  side: Side;
  simTime: number;
}

export interface RecentAbility {
  instanceId: string;
  abilityId: string;
  simTime: number;
}

export interface CombatSnapshot {
  player: UnitRuntimeSnapshot[];
  enemy: UnitRuntimeSnapshot[];
  playerHp: { current: number; max: number };
  enemyHp: { current: number; max: number };
  recentAttacks: RecentAttack[];
  recentAbilities: RecentAbility[];
  finished: boolean;
  winner: Side | null;
}

const RECENT_WINDOW_SEC = 0.6;

function toSnapshot(u: UnitCombatState): UnitRuntimeSnapshot {
  return {
    instanceId: u.instanceId,
    unitId: u.unitId,
    side: u.side,
    position: u.position,
    attackIntervalSec: u.attackIntervalSec,
    lastAttackAt: u.lastAttackAt,
  };
}

/** Replays the event log up to `currentTime` into a point-in-time snapshot for rendering. */
export function useCombatSnapshot(events: CombatEvent[], currentTime: number): CombatSnapshot {
  return useMemo(() => {
    let player: UnitRuntimeSnapshot[] = [];
    let enemy: UnitRuntimeSnapshot[] = [];
    let playerHp = { current: 0, max: 0 };
    let enemyHp = { current: 0, max: 0 };
    const recentAttacks: RecentAttack[] = [];
    const recentAbilities: RecentAbility[] = [];
    let finished = false;
    let winner: Side | null = null;

    for (const event of events) {
      if (event.simTime > currentTime) break;

      switch (event.type) {
        case 'units_init':
          player = event.player.map(toSnapshot);
          enemy = event.enemy.map(toSnapshot);
          playerHp = { current: event.playerHpMax, max: event.playerHpMax };
          enemyHp = { current: event.enemyHpMax, max: event.enemyHpMax };
          break;
        case 'unit_attack_fired': {
          const unit = player.find((u) => u.instanceId === event.instanceId) ?? enemy.find((u) => u.instanceId === event.instanceId);
          if (unit) unit.lastAttackAt = event.simTime;
          if (unit && currentTime - event.simTime <= RECENT_WINDOW_SEC) {
            recentAttacks.push({ instanceId: event.instanceId, side: unit.side, simTime: event.simTime });
          }
          break;
        }
        case 'team_pool_damage':
        case 'team_pool_heal':
          if (event.side === 'player') playerHp = { ...playerHp, current: event.postHp };
          else enemyHp = { ...enemyHp, current: event.postHp };
          break;
        case 'ability_triggered':
          if (currentTime - event.simTime <= RECENT_WINDOW_SEC) {
            recentAbilities.push({ instanceId: event.instanceId, abilityId: event.abilityId, simTime: event.simTime });
          }
          break;
        case 'victory':
          finished = true;
          winner = event.winner;
          break;
      }
    }

    return { player, enemy, playerHp, enemyHp, recentAttacks, recentAbilities, finished, winner };
  }, [events, currentTime]);
}
