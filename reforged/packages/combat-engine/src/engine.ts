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
  /** Run augment effects, applied at t=0 the same way a start_of_combat ability would be — see combatOrchestrator. */
  augmentEffects?: Array<{ effect: AbilityEffect; tagFilter?: string[] }>;
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

// Stacking caps — a support unit firing a team buff every cooldown for up to
// 120s would otherwise break the game (multiplicative stacking with no
// ceiling). These are additive-percent accumulators clamped to this range,
// not a hard multiplier limit, so multiple smaller sources still combine
// naturally up to the cap.
const MAX_HASTE_PERCENT = 100; // attack speed can be buffed at most +100% (2x)
const MAX_SLOW_PERCENT = 80; // attack speed can be slowed at most -80% (0.2x)
const MAX_ATTACK_BUFF_PERCENT = 200; // attack damage can be buffed at most +200% (3x)
const MAX_WEAKEN_PERCENT = 80; // attack damage can be weakened at most -80%
const MAX_POISON_DPS = 40; // stacking poison sources cap out here
const MAX_REGEN_PER_SEC = 30; // stacking regen sources cap out here

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

interface RuntimeUnit {
  instanceId: string;
  unitId: string;
  side: Side;
  position: BoardPosition;
  baseAttackDamage: number; // 0 = no attack stat
  attackDamageBonusPercent: number; // additive, clamped [-MAX_WEAKEN_PERCENT, MAX_ATTACK_BUFF_PERCENT]
  baseAttackIntervalSec: number | null; // null = no attacksPerSecond stat, never acts on a cadence
  attackSpeedBonusPercent: number; // additive, clamped [-MAX_SLOW_PERCENT, MAX_HASTE_PERCENT]
  attackDamage: number; // derived from base + bonus
  attackIntervalSec: number | null; // derived from base + bonus
  triggerMultiplier: number;
  startOfCombatAbilities: Ability[];
  onTriggerAbilities: Ability[];
  lastAttackAt: number;
  abilityCooldowns: Record<string, number>;
  lowHpAbilitiesFired: Set<string>;
}

function recomputeDerivedStats(u: RuntimeUnit): void {
  u.attackDamage = u.baseAttackDamage * (1 + u.attackDamageBonusPercent / 100);
  u.attackIntervalSec = u.baseAttackIntervalSec !== null ? u.baseAttackIntervalSec / (1 + u.attackSpeedBonusPercent / 100) : null;
}

interface Pool {
  hpMax: number;
  hpCurrent: number;
  shield: number;
  shieldDecayPercentPerSec: number;
  poisonDamagePerSec: number;
  lastPoisonTickAt: number;
  regenPerSec: number;
  lastRegenTickAt: number;
}

function otherSide(side: Side): Side {
  return side === 'player' ? 'enemy' : 'player';
}

function uniqueAbilities(abilities: Ability[] | undefined): Ability[] {
  const seen = new Set<string>();
  return (abilities ?? []).filter((ability) => {
    if (seen.has(ability.id)) return false;
    seen.add(ability.id);
    return true;
  });
}

/**
 * Runs a full deterministic combat and returns the complete event log for the
 * client to replay. There is no targeting subsystem: HP is a shared team pool,
 * so every attack/ability effect only ever touches "own pool" or "enemy pool"
 * (or every unit on one side, for team-wide buffs/debuffs). Units never die
 * mid-fight — they act for the whole timeout window, and the pool that first
 * reaches 0 loses (or, at timeout, whichever pool has the higher remaining
 * percentage).
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
    player: {
      hpMax: input.player.hpMax,
      hpCurrent: input.player.hpMax,
      shield: 0,
      shieldDecayPercentPerSec: 0,
      poisonDamagePerSec: 0,
      lastPoisonTickAt: 0,
      regenPerSec: 0,
      lastRegenTickAt: 0,
    },
    enemy: {
      hpMax: input.enemy.hpMax,
      hpCurrent: input.enemy.hpMax,
      shield: 0,
      shieldDecayPercentPerSec: 0,
      poisonDamagePerSec: 0,
      lastPoisonTickAt: 0,
      regenPerSec: 0,
      lastRegenTickAt: 0,
    },
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
        triggerMultiplier: 1,
        appliedBonusIds: [],
      };
      const unit: RuntimeUnit = {
        instanceId: p.instanceId,
        unitId: p.unitId,
        side: team.side,
        position: p.position,
        baseAttackDamage: def.baseStats.attack ?? 0,
        attackDamageBonusPercent: clamp(mod.attackPercent, -MAX_WEAKEN_PERCENT, MAX_ATTACK_BUFF_PERCENT),
        baseAttackIntervalSec: def.baseStats.attacksPerSecond ? 1 / def.baseStats.attacksPerSecond : null,
        attackSpeedBonusPercent: clamp(mod.attackSpeedPercent, -MAX_SLOW_PERCENT, MAX_HASTE_PERCENT),
        attackDamage: 0,
        attackIntervalSec: null,
        triggerMultiplier: mod.triggerMultiplier,
        startOfCombatAbilities: uniqueAbilities(def.startOfCombat),
        onTriggerAbilities: uniqueAbilities(def.onTrigger),
        lastAttackAt: 0,
        abilityCooldowns: {},
        lowHpAbilitiesFired: new Set<string>(),
      };
      recomputeDerivedStats(unit);
      return unit;
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

  function applyPoisonToPool(side: Side, damagePerSec: number) {
    pools[side].poisonDamagePerSec = Math.min(MAX_POISON_DPS, pools[side].poisonDamagePerSec + damagePerSec);
  }

  function applyRegenToPool(side: Side, amountPerSec: number) {
    pools[side].regenPerSec = Math.min(MAX_REGEN_PER_SEC, pools[side].regenPerSec + amountPerSec);
  }

  function buffAttack(unit: RuntimeUnit, percent: number, sourceInstanceId: string | undefined, simTime: number) {
    unit.attackDamageBonusPercent = clamp(unit.attackDamageBonusPercent + percent, -MAX_WEAKEN_PERCENT, MAX_ATTACK_BUFF_PERCENT);
    recomputeDerivedStats(unit);
    log.push({ simTime, type: 'unit_buff_applied', instanceId: unit.instanceId, stat: 'attack', percent, sourceInstanceId });
  }

  function buffAttackSpeed(unit: RuntimeUnit, percent: number, sourceInstanceId: string | undefined, simTime: number) {
    if (unit.baseAttackIntervalSec === null) return;
    unit.attackSpeedBonusPercent = clamp(unit.attackSpeedBonusPercent + percent, -MAX_SLOW_PERCENT, MAX_HASTE_PERCENT);
    recomputeDerivedStats(unit);
    log.push({ simTime, type: 'unit_buff_applied', instanceId: unit.instanceId, stat: 'attackSpeed', percent, sourceInstanceId });
  }

  function applyAbilityEffect(unit: RuntimeUnit, ability: Ability, simTime: number) {
    log.push({ simTime, type: 'ability_triggered', instanceId: unit.instanceId, abilityId: ability.id, trigger: ability.trigger });
    applyEffectFromSide(unit.side, ability.effect, simTime, unit);
  }

  function triggerAbility(unit: RuntimeUnit, ability: Ability, simTime: number): void {
    // Same-trait positional synergy is additive and capped at x2. This keeps
    // two overlapping sources from accidentally turning one authored effect
    // into four or more executions, while still making the synergy visible in
    // the canonical event stream as two real triggers.
    for (let i = 0; i < unit.triggerMultiplier; i++) applyAbilityEffect(unit, ability, simTime);
  }

  function hasAnyTag(u: RuntimeUnit, tagFilter: string[] | undefined): boolean {
    if (!tagFilter) return true;
    const tags = input.unitDefs[u.unitId]?.tags ?? [];
    return tagFilter.some((tag) => tags.includes(tag));
  }

  /**
   * Applies one effect as if cast from `side`. `excludeUnit`, when given, is
   * skipped by team-wide effects (a unit's own team-wide buff hits every
   * OTHER ally, not itself) — omitted entirely for augments, which have no
   * single caster and so affect the whole side uniformly. `tagFilter`
   * (augments only) restricts team-wide/enemy-wide effects to units
   * carrying one of those tags, so an augment can build toward a
   * tag-specific specialization instead of always hitting the whole board.
   */
  function applyEffectFromSide(side: Side, effect: AbilityEffect, simTime: number, excludeUnit?: RuntimeUnit, tagFilter?: string[]) {
    const sourceInstanceId = excludeUnit?.instanceId;
    switch (effect.kind) {
      case 'damage_enemy_pool':
        applyDamageToPool(otherSide(side), effect.amount, 'ability', sourceInstanceId, simTime);
        break;
      case 'heal_own_pool':
        applyHealToPool(side, effect.amount, sourceInstanceId, simTime);
        break;
      case 'shield_own_pool':
        applyShieldToPool(side, effect.amount, effect.decayPercentPerSec ?? 0, sourceInstanceId, simTime);
        break;
      case 'poison_enemy_pool':
        applyPoisonToPool(otherSide(side), effect.damagePerSec);
        break;
      case 'regen_own_pool':
        applyRegenToPool(side, effect.amountPerSec);
        break;
      case 'buff_attack':
        if (excludeUnit) buffAttack(excludeUnit, effect.percent, sourceInstanceId, simTime);
        break;
      case 'buff_attack_speed':
        if (excludeUnit) buffAttackSpeed(excludeUnit, effect.percent, sourceInstanceId, simTime);
        break;
      case 'buff_team_attack':
        for (const ally of units) {
          if (ally.side === side && ally !== excludeUnit && hasAnyTag(ally, tagFilter)) buffAttack(ally, effect.percent, sourceInstanceId, simTime);
        }
        break;
      case 'buff_team_attack_speed':
        for (const ally of units) {
          if (ally.side === side && ally !== excludeUnit && hasAnyTag(ally, tagFilter)) buffAttackSpeed(ally, effect.percent, sourceInstanceId, simTime);
        }
        break;
      case 'weaken_enemy_team_attack':
        for (const foe of units) if (foe.side === otherSide(side) && hasAnyTag(foe, tagFilter)) buffAttack(foe, -effect.percent, sourceInstanceId, simTime);
        break;
      case 'slow_enemy_team_attack_speed':
        for (const foe of units) if (foe.side === otherSide(side) && hasAnyTag(foe, tagFilter)) buffAttackSpeed(foe, -effect.percent, sourceInstanceId, simTime);
        break;
      case 'execute_enemy_pool': {
        const enemySide = otherSide(side);
        const amount = pools[enemySide].hpCurrent * (effect.percentOfCurrentHp / 100);
        if (amount > 0) applyDamageToPool(enemySide, amount, 'ability', sourceInstanceId, simTime);
        break;
      }
      case 'lifesteal_own_pool':
        if (excludeUnit && excludeUnit.attackDamage > 0) {
          applyHealToPool(side, excludeUnit.attackDamage * (effect.percent / 100), sourceInstanceId, simTime);
        }
        break;
      case 'cleanse_own_pool':
        pools[side].poisonDamagePerSec = 0;
        break;
      case 'shred_enemy_shield': {
        const enemyPool = pools[otherSide(side)];
        enemyPool.shield = Math.max(0, enemyPool.shield - effect.amount);
        break;
      }
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
    triggerMultiplier: u.triggerMultiplier,
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
    for (const ability of unit.startOfCombatAbilities) {
      triggerAbility(unit, ability, 0);
    }
  }
  for (const app of input.player.augmentEffects ?? []) applyEffectFromSide('player', app.effect, 0, undefined, app.tagFilter);
  for (const app of input.enemy.augmentEffects ?? []) applyEffectFromSide('enemy', app.effect, 0, undefined, app.tagFilter);

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

        for (const ability of unit.onTriggerAbilities) {
          if (ability.trigger === 'on_attack') triggerAbility(unit, ability, simTime);
        }
      }

      for (const ability of unit.onTriggerAbilities) {
        if (ability.trigger === 'periodic' && ability.periodSec) {
          const last = unit.abilityCooldowns[ability.id] ?? 0;
          if (simTime - last >= ability.periodSec) {
            unit.abilityCooldowns[ability.id] = simTime;
            triggerAbility(unit, ability, simTime);
          }
        }
        if (ability.trigger === 'low_team_hp' && ability.hpThresholdPercent !== undefined) {
          const pool = pools[unit.side];
          const pct = pool.hpCurrent / pool.hpMax;
          if (pct <= ability.hpThresholdPercent && !unit.lowHpAbilitiesFired.has(ability.id)) {
            unit.lowHpAbilitiesFired.add(ability.id);
            triggerAbility(unit, ability, simTime);
          }
        }
      }
    }

    for (const side of ['player', 'enemy'] as const) {
      const pool = pools[side];
      if (pool.shield > 0 && pool.shieldDecayPercentPerSec > 0) {
        pool.shield = Math.max(0, pool.shield * (1 - (pool.shieldDecayPercentPerSec / 100) * dt));
      }
      if (pool.poisonDamagePerSec > 0 && simTime - pool.lastPoisonTickAt >= 1) {
        pool.lastPoisonTickAt = simTime;
        applyDamageToPool(side, pool.poisonDamagePerSec, 'ability', undefined, simTime);
      }
      if (pool.regenPerSec > 0 && simTime - pool.lastRegenTickAt >= 1) {
        pool.lastRegenTickAt = simTime;
        applyHealToPool(side, pool.regenPerSec, undefined, simTime);
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
