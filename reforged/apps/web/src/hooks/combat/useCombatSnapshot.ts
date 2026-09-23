import { useMemo } from 'react';
import type { BoardPosition, CombatEvent, Side, UnitCombatState } from '@reforged/schema';

export interface UnitRuntimeSnapshot {
  instanceId: string;
  unitId: string;
  side: Side;
  position: BoardPosition;
  attackIntervalSec: number | null;
  lastAttackAt: number;
  triggerMultiplier: number;
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

export interface UnitBuffState {
  attackPercent: number;
  attackSpeedPercent: number;
  strengthStacks: number;
}

/** Team-pool-wide status, current as of `currentTime` — see team_pool_shield_applied / team_pool_stat_applied. */
export interface TeamStatus {
  shield: number;
  poisonDamagePerSec: number;
  strengthStacks: number;
  hasteStacks: number;
  slowPercent: number;
  weakenPercent: number;
  dodgeStacks: number;
  fragilityPercent: number;
  thornsPercent: number;
  vampirismPercent: number;
  executionStacks: number;
}

function emptyTeamStatus(): TeamStatus {
  return { shield: 0, poisonDamagePerSec: 0, strengthStacks: 0, hasteStacks: 0, slowPercent: 0, weakenPercent: 0, dodgeStacks: 0, fragilityPercent: 0, thornsPercent: 0, vampirismPercent: 0, executionStacks: 0 };
}

export interface CombatSnapshot {
  player: UnitRuntimeSnapshot[];
  enemy: UnitRuntimeSnapshot[];
  playerHp: { current: number; max: number };
  enemyHp: { current: number; max: number };
  playerStatus: TeamStatus;
  enemyStatus: TeamStatus;
  recentAttacks: RecentAttack[];
  recentAbilities: RecentAbility[];
  /** Cumulative buff/debuff % per unit, accrued from every unit_buff_applied event up to currentTime. */
  unitBuffs: Record<string, UnitBuffState>;
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
    triggerMultiplier: u.triggerMultiplier,
  };
}

function buffFor(unitBuffs: Record<string, UnitBuffState>, instanceId: string): UnitBuffState {
  let entry = unitBuffs[instanceId];
  if (!entry) {
    entry = { attackPercent: 0, attackSpeedPercent: 0, strengthStacks: 0 };
    unitBuffs[instanceId] = entry;
  }
  return entry;
}

/** Replays the event log up to `currentTime` into a point-in-time snapshot for rendering. */
export function useCombatSnapshot(events: CombatEvent[], currentTime: number): CombatSnapshot {
  return useMemo(() => {
    let player: UnitRuntimeSnapshot[] = [];
    let enemy: UnitRuntimeSnapshot[] = [];
    let playerHp = { current: 0, max: 0 };
    let enemyHp = { current: 0, max: 0 };
    const playerStatus = emptyTeamStatus();
    const enemyStatus = emptyTeamStatus();
    const recentAttacks: RecentAttack[] = [];
    const recentAbilities: RecentAbility[] = [];
    const unitBuffs: Record<string, UnitBuffState> = {};
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
          if (event.side === 'player') {
            playerHp = { ...playerHp, current: event.postHp };
            playerStatus.shield = event.postShield;
          } else {
            enemyHp = { ...enemyHp, current: event.postHp };
            enemyStatus.shield = event.postShield;
          }
          break;
        case 'team_pool_heal':
          if (event.side === 'player') playerHp = { ...playerHp, current: event.postHp };
          else enemyHp = { ...enemyHp, current: event.postHp };
          break;
        case 'team_pool_shield_applied': {
          const status = event.side === 'player' ? playerStatus : enemyStatus;
          status.shield = event.postShield;
          break;
        }
        case 'team_pool_poison_changed': {
          const status = event.side === 'player' ? playerStatus : enemyStatus;
          status.poisonDamagePerSec = event.total;
          break;
        }
        case 'team_pool_stat_applied': {
          const status = event.side === 'player' ? playerStatus : enemyStatus;
          if (event.stat === 'strength') status.strengthStacks = event.total;
          else if (event.stat === 'haste') status.hasteStacks = event.total;
          else if (event.stat === 'slow') status.slowPercent = event.total;
          else if (event.stat === 'weaken') status.weakenPercent = event.total;
          else if (event.stat === 'dodge') status.dodgeStacks = event.total;
          else if (event.stat === 'fragility') status.fragilityPercent = event.total;
          else if (event.stat === 'thorns') status.thornsPercent = event.total;
          else if (event.stat === 'vampirism') status.vampirismPercent = event.total;
          else if (event.stat === 'execution') status.executionStacks = event.total;
          break;
        }
        case 'ability_triggered':
          if (currentTime - event.simTime <= RECENT_WINDOW_SEC) {
            recentAbilities.push({ instanceId: event.instanceId, abilityId: event.abilityId, simTime: event.simTime });
          }
          break;
        case 'unit_buff_applied': {
          const entry = buffFor(unitBuffs, event.instanceId);
          if (event.stat === 'attack') entry.attackPercent += event.percent;
          else if (event.stat === 'strength') entry.strengthStacks += event.percent;
          else entry.attackSpeedPercent += event.percent;
          break;
        }
        case 'victory':
          finished = true;
          winner = event.winner;
          break;
      }
    }

    return { player, enemy, playerHp, enemyHp, playerStatus, enemyStatus, recentAttacks, recentAbilities, unitBuffs, finished, winner };
  }, [events, currentTime]);
}
