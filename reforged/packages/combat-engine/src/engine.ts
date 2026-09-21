import type { Ability, AbilityEffect, BoardPosition, CombatLog, Side, UnitCombatState, UnitDef } from '@reforged/schema';
import { EventLogBuilder } from './eventLog.js';
import { resolvePositionalBonuses } from './positionalResolver.js';

export interface CombatParticipantInput {
  instanceId: string;
  unitId: string;
  position: BoardPosition;
}

export interface CombatTeamInput {
  side: Side;
  units: CombatParticipantInput[];
  /** Team pool max HP — computed by the caller (e.g. from run/level scaling). */
  hpMax: number;
}

export interface RunCombatInput {
  combatId: string;
  seed: number;
  player: CombatTeamInput;
  enemy: CombatTeamInput;
  unitDefs: Record<string, UnitDef>;
  /** Simulation tick size in seconds. Defaults to 0.1, matching the legacy engine's cadence. */
  dt?: number;
  /** Simulation timeout in seconds. Defaults to 120, matching the legacy engine. */
  timeoutSec?: number;
}

interface RuntimeUnit {
  instanceId: string;
  unitId: string;
  side: Side;
  position: BoardPosition;
  /** null = this unit has no attacksPerSecond stat and never acts on a cadence at all. */
  attackIntervalSec: number | null;
  /** 0 = this unit has no attack stat — it can still act on its cadence (on_attack abilities), it just deals no pool damage. */
  attackDamage: number;
  lastAttackAt: number;
  abilityCooldowns: Record<string, number>;
  lowHpAbilitiesFired: Set<string>;
}

interface Pool {
  hpMax: number;
  hpCurrent: number;
  shield: number;
  shieldDecayPercentPerSec: number;
}

function otherSide(side: Side): Side {
  return side === 'player' ? 'enemy' : 'player';
}

/**
 * Runs a full deterministic combat and returns the complete event log for the
 * client to replay. There is no targeting subsystem: HP is a shared team pool,
 * so every attack/ability effect only ever touches "own pool" or "enemy pool".
 * Units never die mid-fight — they act for the whole timeout window, and the
 * pool that first reaches 0 loses (or, at timeout, whichever pool has the
 * higher remaining percentage).
 *
 * No defense stat exists — damage is never mitigated. attack/attacksPerSecond
 * are both optional per unit: a unit with attacksPerSecond but no attack
 * still triggers its on_attack abilities on schedule (a pure support unit
 * that casts a buff/heal/shield every cooldown instead of dealing damage); a
 * unit with neither only acts through start_of_combat/periodic/low_team_hp.
 */
export function runCombat(input: RunCombatInput): CombatLog {
  const dt = input.dt ?? 0.1;
  const timeoutSec = input.timeoutSec ?? 120;
  const log = new EventLogBuilder();

  const pools: Record<Side, Pool> = {
    player: { hpMax: input.player.hpMax, hpCurrent: input.player.hpMax, shield: 0, shieldDecayPercentPerSec: 0 },
    enemy: { hpMax: input.enemy.hpMax, hpCurrent: input.enemy.hpMax, shield: 0, shieldDecayPercentPerSec: 0 },
  };

  const positionalMods = {
    player: resolvePositionalBonuses(input.player.units, input.unitDefs),
    enemy: resolvePositionalBonuses(input.enemy.units, input.unitDefs),
  };

  function buildRuntimeUnits(team: CombatTeamInput): RuntimeUnit[] {
    return team.units.map((p) => {
      const def = input.unitDefs[p.unitId];
      if (!def) throw new Error(`Unknown unitId "${p.unitId}"`);
      const mod = positionalMods[team.side][p.instanceId] ?? {
        attackPercent: 0,
        attackSpeedPercent: 0,
        appliedBonusIds: [],
      };
      const attacksPerSecond = def.baseStats.attacksPerSecond
        ? def.baseStats.attacksPerSecond * (1 + mod.attackSpeedPercent / 100)
        : null;
      return {
        instanceId: p.instanceId,
        unitId: p.unitId,
        side: team.side,
        position: p.position,
        attackIntervalSec: attacksPerSecond ? 1 / attacksPerSecond : null,
        attackDamage: def.baseStats.attack ? def.baseStats.attack * (1 + mod.attackPercent / 100) : 0,
        lastAttackAt: 0,
        abilityCooldowns: {},
        lowHpAbilitiesFired: new Set<string>(),
      };
    });
  }

  const units: RuntimeUnit[] = [...buildRuntimeUnits(input.player), ...buildRuntimeUnits(input.enemy)];

  function applyDamageToPool(side: Side, amount: number, cause: 'attack' | 'ability', sourceInstanceId: string | undefined, simTime: number) {
    const pool = pools[side];
    let effective = amount;
    if (pool.shield > 0) {
      const absorbed = Math.min(pool.shield, effective);
      pool.shield -= absorbed;
      effective -= absorbed;
    }
    pool.hpCurrent = Math.max(0, pool.hpCurrent - effective);
    log.push({ simTime, type: 'team_pool_damage', side, amount: effective, postHp: pool.hpCurrent, cause, sourceInstanceId });
  }

  function applyHealToPool(side: Side, amount: number, sourceInstanceId: string | undefined, simTime: number) {
    const pool = pools[side];
    pool.hpCurrent = Math.min(pool.hpMax, pool.hpCurrent + amount);
    log.push({ simTime, type: 'team_pool_heal', side, amount, postHp: pool.hpCurrent, sourceInstanceId });
  }

  function applyShieldToPool(side: Side, amount: number, decayPercentPerSec: number, sourceInstanceId: string | undefined, simTime: number) {
    pools[side].shield += amount;
    pools[side].shieldDecayPercentPerSec = decayPercentPerSec;
    log.push({ simTime, type: 'team_pool_shield_applied', side, amount, sourceInstanceId });
  }

  function applyAbilityEffect(unit: RuntimeUnit, ability: Ability, simTime: number) {
    log.push({ simTime, type: 'ability_triggered', instanceId: unit.instanceId, abilityId: ability.id, trigger: ability.trigger });
    const effect: AbilityEffect = ability.effect;
    switch (effect.kind) {
      case 'damage_enemy_pool':
        applyDamageToPool(otherSide(unit.side), effect.amount, 'ability', unit.instanceId, simTime);
        break;
      case 'heal_own_pool':
        applyHealToPool(unit.side, effect.amount, unit.instanceId, simTime);
        break;
      case 'shield_own_pool':
        applyShieldToPool(unit.side, effect.amount, effect.decayPercentPerSec ?? 0, unit.instanceId, simTime);
        break;
      case 'buff_attack':
        unit.attackDamage *= 1 + effect.percent / 100;
        log.push({ simTime, type: 'unit_buff_applied', instanceId: unit.instanceId, stat: 'attack', percent: effect.percent, sourceInstanceId: unit.instanceId });
        break;
      case 'buff_attack_speed':
        if (unit.attackIntervalSec !== null) {
          unit.attackIntervalSec /= 1 + effect.percent / 100;
          log.push({ simTime, type: 'unit_buff_applied', instanceId: unit.instanceId, stat: 'attackSpeed', percent: effect.percent, sourceInstanceId: unit.instanceId });
        }
        break;
      case 'buff_team_attack':
        for (const ally of units) {
          if (ally.side === unit.side && ally.instanceId !== unit.instanceId) {
            ally.attackDamage *= 1 + effect.percent / 100;
            log.push({ simTime, type: 'unit_buff_applied', instanceId: ally.instanceId, stat: 'attack', percent: effect.percent, sourceInstanceId: unit.instanceId });
          }
        }
        break;
      case 'buff_team_attack_speed':
        for (const ally of units) {
          if (ally.side === unit.side && ally.instanceId !== unit.instanceId && ally.attackIntervalSec !== null) {
            ally.attackIntervalSec /= 1 + effect.percent / 100;
            log.push({ simTime, type: 'unit_buff_applied', instanceId: ally.instanceId, stat: 'attackSpeed', percent: effect.percent, sourceInstanceId: unit.instanceId });
          }
        }
        break;
    }
  }

  const combatUnitStates: UnitCombatState[] = units.map((u) => ({
    instanceId: u.instanceId,
    unitId: u.unitId,
    side: u.side,
    position: u.position,
    attackIntervalSec: u.attackIntervalSec,
    lastAttackAt: 0,
    abilityCooldowns: {},
    positionalBonusesApplied: positionalMods[u.side][u.instanceId]?.appliedBonusIds ?? [],
  }));

  log.push({
    simTime: 0,
    type: 'units_init',
    player: combatUnitStates.filter((u) => u.side === 'player'),
    enemy: combatUnitStates.filter((u) => u.side === 'enemy'),
    playerHpMax: pools.player.hpMax,
    enemyHpMax: pools.enemy.hpMax,
  });
  log.push({ simTime: 0, type: 'start' });

  for (const unit of units) {
    const def = input.unitDefs[unit.unitId];
    for (const ability of def.startOfCombat ?? []) {
      applyAbilityEffect(unit, ability, 0);
    }
  }

  let winner: Side | null = null;
  let simTime = 0;

  while (simTime < timeoutSec) {
    for (const unit of units) {
      const def = input.unitDefs[unit.unitId];

      if (unit.attackIntervalSec !== null && simTime - unit.lastAttackAt >= unit.attackIntervalSec) {
        unit.lastAttackAt = simTime;
        log.push({ simTime, type: 'unit_attack_fired', instanceId: unit.instanceId, emoji: def.emoji });
        if (unit.attackDamage > 0) {
          applyDamageToPool(otherSide(unit.side), unit.attackDamage, 'attack', unit.instanceId, simTime);
        }

        for (const ability of def.onTrigger ?? []) {
          if (ability.trigger === 'on_attack') applyAbilityEffect(unit, ability, simTime);
        }
      }

      for (const ability of def.onTrigger ?? []) {
        if (ability.trigger === 'periodic' && ability.periodSec) {
          const last = unit.abilityCooldowns[ability.id] ?? 0;
          if (simTime - last >= ability.periodSec) {
            unit.abilityCooldowns[ability.id] = simTime;
            applyAbilityEffect(unit, ability, simTime);
          }
        }
        if (ability.trigger === 'low_team_hp' && ability.hpThresholdPercent !== undefined) {
          const pool = pools[unit.side];
          const pct = pool.hpCurrent / pool.hpMax;
          if (pct <= ability.hpThresholdPercent && !unit.lowHpAbilitiesFired.has(ability.id)) {
            unit.lowHpAbilitiesFired.add(ability.id);
            applyAbilityEffect(unit, ability, simTime);
          }
        }
      }
    }

    for (const side of ['player', 'enemy'] as const) {
      const pool = pools[side];
      if (pool.shield > 0 && pool.shieldDecayPercentPerSec > 0) {
        pool.shield = Math.max(0, pool.shield * (1 - (pool.shieldDecayPercentPerSec / 100) * dt));
      }
    }

    if (pools.player.hpCurrent <= 0 || pools.enemy.hpCurrent <= 0) {
      if (pools.player.hpCurrent <= 0 && pools.enemy.hpCurrent <= 0) {
        winner = pools.player.hpCurrent <= pools.enemy.hpCurrent ? 'enemy' : 'player';
      } else {
        winner = pools.player.hpCurrent <= 0 ? 'enemy' : 'player';
      }
      break;
    }

    simTime = Math.round((simTime + dt) * 1000) / 1000;
  }

  if (!winner) {
    const playerPct = pools.player.hpCurrent / pools.player.hpMax;
    const enemyPct = pools.enemy.hpCurrent / pools.enemy.hpMax;
    winner = playerPct >= enemyPct ? 'player' : 'enemy';
  }

  log.push({ simTime, type: 'victory', winner });
  log.push({ simTime, type: 'end' });

  return { combatId: input.combatId, seed: input.seed, events: log.build() };
}
