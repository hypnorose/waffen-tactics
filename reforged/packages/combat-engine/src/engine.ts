import type { Ability, AbilityEffect, BoardPosition, CombatLog, ReactionEffect, Side, UnitCombatState, UnitDef } from '@reforged/schema';
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
// ceiling). These are additive accumulators clamped to a range, not a hard
// multiplier limit, so multiple smaller sources still combine naturally up
// to the cap.
const MAX_HASTE_PERCENT = 100; // per-unit attackSpeedBonusPercent ceiling (positional/self buffs)
const MAX_SLOW_PERCENT = 80;
const MAX_ATTACK_BUFF_PERCENT = 200;
const MAX_STRENGTH_STACKS = 200;
const MAX_WEAKEN_PERCENT = 80;
// Poison is a persistent pool threat and bypasses shield/dodge. It has no
// stacking cap: every authored source remains relevant to poison payoffs.
const MAX_REGEN_PER_SEC = 30;
const MAX_HASTE_STACKS = 100; // pool-level haste — 1 stack = 1%, combined with per-unit speed at read time
const MAX_DODGE_STACKS = 70;
const MAX_FRAGILITY_PERCENT = 150;
const MAX_THORNS_PERCENT = 100;
const MAX_VAMPIRISM_PERCENT = 80;
const MAX_EXECUTION_STACKS = 30;
// Absolute HP, not a percentage — execution is a finisher for a pool that's
// already a sliver from HP away from dead, not a build-around instakill on a
// team still sitting on a real chunk of health. Even fully invested (every
// execution_empower_enemy_pool augment picked) this caps out at a fraction
// of any real team pool's size.
const MAX_EXECUTION_HP_THRESHOLD = 20;
const MAX_MULTICAST_EXTRA_HITS = 5;
const MAX_SHRED_ON_HIT_STACKS = 10;
const EXECUTION_DEFAULT_HP_THRESHOLD = 3; // absolute HP, not a percentage
const EXECUTION_DEFAULT_STACKS_REQUIRED = 10;
const MULTICAST_HIT_DELAY_SEC = 0.15;
const MAX_REACTION_DEPTH = 4; // guards against a reaction whose own effect re-triggers itself

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

// Deterministic PRNG (mulberry32) seeded from input.seed — dodge is the only
// probabilistic mechanic in the engine, and the "same seed -> same events"
// guarantee (see engine.test.ts) depends on never touching Math.random().
function createRng(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

interface RuntimeUnit {
  instanceId: string;
  unitId: string;
  side: Side;
  position: BoardPosition;
  baseAttackDamage: number; // 0 = no attack stat
  attackDamageBonusPercent: number; // additive, clamped [-MAX_WEAKEN_PERCENT, MAX_ATTACK_BUFF_PERCENT]
  strengthStacks: number; // personal positional Strength, 1 stack = 1% attack
  baseAttackIntervalSec: number | null; // null = no attacksPerSecond stat, never acts on a cadence
  attackSpeedBonusPercent: number; // per-unit additive, clamped [-MAX_SLOW_PERCENT, MAX_HASTE_PERCENT]
  attackDamage: number; // derived from base + bonus
  attackIntervalSec: number | null; // derived from base + bonus + pool haste stacks
  triggerMultiplier: number;
  startOfCombatAbilities: Ability[];
  onTriggerAbilities: Ability[];
  lastAttackAt: number;
  abilityCooldowns: Record<string, number>;
  lowHpAbilitiesFired: Set<string>;
  // Set by multicast_team / shred_dodge_on_hit_team augment effects.
  multicastExtraHits: number;
  multicastExtraHitPercent: number;
  shredDodgeOnHitStacks: number;
  executionMarkOnHitStacks: number;
  // Set by a grant_slow_on_attack positional bonus — fires on this unit's
  // own on_trigger cadence, not gated on it actually dealing damage.
  slowOnAttackPercent: number;
  /** Set by a grant_shield_on_trigger positional bonus. */
  shieldOnTriggerAmount: number;
}

function recomputeDerivedStats(u: RuntimeUnit, pool: Pool): void {
  u.attackDamage = u.baseAttackDamage * (1 + (u.attackDamageBonusPercent + u.strengthStacks + pool.strengthStacks - pool.weakenPercent) / 100);
  if (u.baseAttackIntervalSec === null) {
    u.attackIntervalSec = null;
    return;
  }
  const effectiveSpeedPercent = clamp(u.attackSpeedBonusPercent + pool.hasteStacks - pool.slowPercent, -MAX_SLOW_PERCENT, MAX_HASTE_PERCENT);
  u.attackIntervalSec = u.baseAttackIntervalSec / (1 + effectiveSpeedPercent / 100);
}

type ReactionHook = 'shield_gained' | 'shield_depleted';

interface Pool {
  hpMax: number;
  hpCurrent: number;
  shield: number; // never decays on its own — only consumed by damage
  poisonDamagePerSec: number;
  lastPoisonTickAt: number;
  regenPerSec: number;
  lastRegenTickAt: number;
  strengthStacks: number; // 1 stack = 1% attack, team-wide
  hasteStacks: number; // 1 stack = 1% attack speed, team-wide
  slowPercent: number; // % attack-speed reduction, team-wide
  weakenPercent: number; // % attack reduction, team-wide
  dodgeStacks: number; // 1 stack = 1% chance to fully negate an incoming hit
  fragilityPercent: number; // % more damage taken from every source
  thornsPercent: number; // % of own HP loss reflected back at the enemy pool
  vampirismPercent: number; // % of damage dealt by any unit on this side healed back to it
  executionStacks: number;
  executionHpThreshold: number; // absolute HP, not a percentage
  executionStacksRequired: number;
  momentumHasteStacksPerSec: number;
  momentumAttackPercentPerSec: number;
  lastMomentumTickAt: number;
  reactions: Array<{ on: ReactionHook; effect: ReactionEffect }>;
  shieldGainReductionPercent: number;
  shieldGainBonusFlat: number;
}

function makePool(hpMax: number): Pool {
  return {
    hpMax,
    hpCurrent: hpMax,
    shield: 0,
    poisonDamagePerSec: 0,
    lastPoisonTickAt: 0,
    regenPerSec: 0,
    lastRegenTickAt: 0,
    strengthStacks: 0,
    hasteStacks: 0,
    slowPercent: 0,
    weakenPercent: 0,
    dodgeStacks: 0,
    fragilityPercent: 0,
    thornsPercent: 0,
    vampirismPercent: 0,
    executionStacks: 0,
    executionHpThreshold: EXECUTION_DEFAULT_HP_THRESHOLD,
    executionStacksRequired: EXECUTION_DEFAULT_STACKS_REQUIRED,
    momentumHasteStacksPerSec: 0,
    momentumAttackPercentPerSec: 0,
    lastMomentumTickAt: 0,
    reactions: [],
    shieldGainReductionPercent: 0,
    shieldGainBonusFlat: 0,
  };
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
 * percentage). Egzekucja (execution) is the one exception: it sets a pool's
 * HP straight to 0 outside the normal damage pipeline once its current HP
 * drops to a sliver (a few absolute HP, not a percentage of max) AND its
 * mark count crosses the required threshold — a finisher for a pool that's
 * already effectively dead, not a build-around instakill.
 *
 * No defense stat exists — damage is never mitigated except by shield, dodge
 * and fragility, all team-pool-wide statuses (never per-unit — see the note
 * at the top of augments.ts on why every status here lives on the pool).
 */
export function runCombat(input: RunCombatInput): CombatLog {
  const dt = input.dt ?? 0.1;
  const timeoutSec = input.timeoutSec ?? 120;
  const log = new EventLogBuilder();
  const rng = createRng(input.seed);

  const pools: Record<Side, Pool> = {
    player: makePool(input.player.hpMax),
    enemy: makePool(input.enemy.hpMax),
  };

  const positionalMods = resolvePositionalBonuses(input.player.units, input.unitDefs);
  const enemyPositionalMods = resolvePositionalBonuses(input.enemy.units, input.unitDefs);
  const positionalModsBySide: Record<Side, ReturnType<typeof resolvePositionalBonuses>> = {
    player: positionalMods,
    enemy: enemyPositionalMods,
  };

  function buildRuntimeUnits(team: CombatTeamInput): RuntimeUnit[] {
    return team.units.map((p) => {
      const def = input.unitDefs[p.unitId];
      if (!def) throw new Error(`Unknown unitId "${p.unitId}"`);
      const mod = positionalModsBySide[team.side][p.instanceId] ?? {
        attackPercent: 0,
        attackSpeedPercent: 0,
        triggerMultiplier: 1,
        slowOnAttackPercent: 0,
        shieldOnTriggerAmount: 0,
        strengthStacks: 0,
        appliedBonusIds: [],
      };
      const unit: RuntimeUnit = {
        instanceId: p.instanceId,
        unitId: p.unitId,
        side: team.side,
        position: p.position,
        baseAttackDamage: def.baseStats.attack ?? 0,
        attackDamageBonusPercent: clamp(mod.attackPercent, -MAX_WEAKEN_PERCENT, MAX_ATTACK_BUFF_PERCENT),
        strengthStacks: Math.min(MAX_STRENGTH_STACKS, mod.strengthStacks),
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
        multicastExtraHits: 0,
        multicastExtraHitPercent: 0,
        shredDodgeOnHitStacks: 0,
        executionMarkOnHitStacks: 0,
        slowOnAttackPercent: mod.slowOnAttackPercent,
        shieldOnTriggerAmount: mod.shieldOnTriggerAmount,
      };
      recomputeDerivedStats(unit, pools[team.side]);
      return unit;
    });
  }

  const units: RuntimeUnit[] = [...buildRuntimeUnits(input.player), ...buildRuntimeUnits(input.enemy)];

  function recomputeAllUnits(side: Side) {
    const pool = pools[side];
    for (const u of units) if (u.side === side) recomputeDerivedStats(u, pool);
  }

  let reactionDepth = 0;
  function fireReactions(side: Side, on: ReactionHook, simTime: number) {
    if (reactionDepth >= MAX_REACTION_DEPTH) return;
    reactionDepth++;
    for (const r of pools[side].reactions) {
      if (r.on === on) applyReactionEffect(side, r.effect, simTime);
    }
    reactionDepth--;
  }

  function applyReactionEffect(side: Side, effect: ReactionEffect, simTime: number) {
    switch (effect.kind) {
      case 'grant_haste_stacks':
        grantHaste(side, effect.stacks, undefined, simTime);
        break;
      case 'grant_dodge_stacks':
        grantDodge(side, effect.stacks, undefined, simTime);
        break;
      case 'grant_shield':
        applyShieldToPool(side, effect.amount, undefined, simTime);
        break;
      case 'damage_enemy_pool':
        applyDamageToPool(otherSide(side), effect.amount, 'ability', undefined, simTime);
        break;
      case 'buff_team_attack':
        for (const ally of units) if (ally.side === side) buffAttack(ally, effect.percent, undefined, simTime);
        break;
    }
  }

  function finalizeDamage(side: Side, amount: number, cause: 'attack' | 'ability', sourceInstanceId: string | undefined, simTime: number, allowThornsReflection: boolean) {
    const pool = pools[side];
    pool.hpCurrent = Math.max(0, pool.hpCurrent - amount);
    // Always push, even at amount 0 (a hit fully absorbed by shield) — the
    // client needs postShield to stay current on every hit, not just ones
    // that broke through to HP.
    log.push({ simTime, type: 'team_pool_damage', side, amount, postHp: pool.hpCurrent, postShield: pool.shield, cause, sourceInstanceId });
    if (allowThornsReflection && amount > 0 && pool.thornsPercent > 0) {
      const reflect = amount * (pool.thornsPercent / 100);
      if (reflect > 0) applyDamageToPool(otherSide(side), reflect, 'ability', undefined, simTime, true);
    }
    // Vampirism credits whoever dealt this hit, not the victim. Poison is a
    // status tick, not a landed hit, and pool-wide damage without a unit
    // source is not something the attacking team should lifesteal from.
    if (allowThornsReflection && amount > 0 && (cause === 'attack' || sourceInstanceId !== undefined)) {
      const attackerSide = otherSide(side);
      const attackerPool = pools[attackerSide];
      if (attackerPool.vampirismPercent > 0) applyHealToPool(attackerSide, amount * (attackerPool.vampirismPercent / 100), sourceInstanceId, simTime);
    }
    checkExecution(side, simTime);
  }

  function checkExecution(side: Side, simTime: number) {
    const pool = pools[side];
    if (pool.hpCurrent <= 0) return;
    if (pool.hpCurrent <= pool.executionHpThreshold && pool.executionStacks >= pool.executionStacksRequired) {
      pool.hpCurrent = 0;
      log.push({ simTime, type: 'team_pool_executed', side });
    }
  }

  // `isReflection` marks damage that itself came from a thorns reflection —
  // it still rolls dodge/shield/fragility normally, it just can't spawn a
  // second reflection (that would be an infinite ping-pong between two
  // thorns-carrying sides).
  function applyDamageToPool(side: Side, amount: number, cause: 'attack' | 'ability', sourceInstanceId: string | undefined, simTime: number, isReflection = false) {
    const pool = pools[side];
    if (pool.dodgeStacks > 0) {
      const chance = Math.min(pool.dodgeStacks, MAX_DODGE_STACKS) / 100;
      if (rng() < chance) {
        log.push({ simTime, type: 'team_pool_dodge_proc', side, negatedAmount: amount });
        return;
      }
    }
    let effective = amount;
    if (pool.fragilityPercent > 0) effective *= 1 + pool.fragilityPercent / 100;
    if (pool.shield > 0) {
      const absorbed = Math.min(pool.shield, effective);
      pool.shield -= absorbed;
      effective -= absorbed;
      if (absorbed > 0 && pool.shield <= 0) fireReactions(side, 'shield_depleted', simTime);
    }
    finalizeDamage(side, effective, cause, sourceInstanceId, simTime, !isReflection);
  }

  // Poison is a status, not a hit — it ignores dodge and shield entirely
  // (only fragility still amplifies it, and cleanse is the only counter).
  function applyPoisonTick(side: Side, damagePerSec: number, simTime: number) {
    const pool = pools[side];
    let effective = damagePerSec;
    if (pool.fragilityPercent > 0) effective *= 1 + pool.fragilityPercent / 100;
    finalizeDamage(side, effective, 'ability', undefined, simTime, true);
  }

  function applyHealToPool(side: Side, amount: number, sourceInstanceId: string | undefined, simTime: number) {
    const pool = pools[side];
    pool.hpCurrent = Math.min(pool.hpMax, pool.hpCurrent + amount);
    log.push({ simTime, type: 'team_pool_heal', side, amount, postHp: pool.hpCurrent, sourceInstanceId });
  }

  function applyShieldToPool(side: Side, amount: number, sourceInstanceId: string | undefined, simTime: number) {
    const pool = pools[side];
    const wasZero = pool.shield <= 0;
    const boostedAmount = amount + pool.shieldGainBonusFlat;
    const granted = pool.shieldGainReductionPercent > 0
      ? boostedAmount * (1 - Math.min(100, pool.shieldGainReductionPercent) / 100)
      : boostedAmount;
    pool.shield += granted;
    if (granted !== 0) log.push({ simTime, type: 'team_pool_shield_applied', side, amount: granted, postShield: pool.shield, sourceInstanceId });
    if (wasZero && pool.shield > 0) fireReactions(side, 'shield_gained', simTime);
  }

  // Removes shield without dealing damage. The negative shield event is used
  // by both steal_buff and the all-buff purge so the replay can show the
  // removal instead of silently changing the pool.
  function removeShield(side: Side, amount: number, simTime: number): number {
    const pool = pools[side];
    const wasPositive = pool.shield > 0;
    const removed = Math.min(pool.shield, amount);
    pool.shield -= removed;
    if (removed > 0) log.push({ simTime, type: 'team_pool_shield_applied', side, amount: -removed, postShield: pool.shield });
    if (wasPositive && pool.shield <= 0) fireReactions(side, 'shield_depleted', simTime);
    return removed;
  }

  function applyPoisonToPool(side: Side, damagePerSec: number, sourceInstanceId: string | undefined, simTime: number) {
    const pool = pools[side];
    const before = pool.poisonDamagePerSec;
    pool.poisonDamagePerSec += damagePerSec;
    if (pool.poisonDamagePerSec !== before) {
      log.push({
        simTime,
        type: 'team_pool_poison_changed',
        side,
        amount: pool.poisonDamagePerSec - before,
        total: pool.poisonDamagePerSec,
        sourceInstanceId,
      });
    }
  }

  function applyRegenToPool(side: Side, amountPerSec: number) {
    pools[side].regenPerSec = Math.min(MAX_REGEN_PER_SEC, pools[side].regenPerSec + amountPerSec);
  }

  function grantHaste(side: Side, stacks: number, sourceInstanceId: string | undefined, simTime: number) {
    const pool = pools[side];
    const before = pool.hasteStacks;
    pool.hasteStacks = clamp(pool.hasteStacks + stacks, 0, MAX_HASTE_STACKS);
    if (pool.hasteStacks !== before) {
      log.push({ simTime, type: 'team_pool_stat_applied', side, stat: 'haste', amount: pool.hasteStacks - before, total: pool.hasteStacks, sourceInstanceId });
      recomputeAllUnits(side);
    }
  }

  function grantSlow(side: Side, percent: number, sourceInstanceId: string | undefined, simTime: number) {
    const pool = pools[side];
    const before = pool.slowPercent;
    pool.slowPercent = clamp(pool.slowPercent + percent, 0, MAX_SLOW_PERCENT);
    if (pool.slowPercent !== before) {
      log.push({ simTime, type: 'team_pool_stat_applied', side, stat: 'slow', amount: pool.slowPercent - before, total: pool.slowPercent, sourceInstanceId });
      recomputeAllUnits(side);
    }
  }

  function grantWeaken(side: Side, percent: number, sourceInstanceId: string | undefined, simTime: number) {
    const pool = pools[side];
    const before = pool.weakenPercent;
    pool.weakenPercent = clamp(pool.weakenPercent + percent, 0, MAX_WEAKEN_PERCENT);
    if (pool.weakenPercent !== before) {
      log.push({ simTime, type: 'team_pool_stat_applied', side, stat: 'weaken', amount: pool.weakenPercent - before, total: pool.weakenPercent, sourceInstanceId });
      recomputeAllUnits(side);
    }
  }

  function grantStrength(side: Side, stacks: number, sourceInstanceId: string | undefined, simTime: number) {
    const pool = pools[side];
    const before = pool.strengthStacks;
    pool.strengthStacks = clamp(pool.strengthStacks + stacks, 0, MAX_STRENGTH_STACKS);
    if (pool.strengthStacks !== before) {
      log.push({ simTime, type: 'team_pool_stat_applied', side, stat: 'strength', amount: pool.strengthStacks - before, total: pool.strengthStacks, sourceInstanceId });
      recomputeAllUnits(side);
    }
  }

  function shredHaste(side: Side, stacks: number, simTime: number) {
    const pool = pools[side];
    const before = pool.hasteStacks;
    pool.hasteStacks = clamp(pool.hasteStacks - stacks, 0, MAX_HASTE_STACKS);
    if (pool.hasteStacks !== before) {
      log.push({ simTime, type: 'team_pool_stat_applied', side, stat: 'haste', amount: pool.hasteStacks - before, total: pool.hasteStacks });
      recomputeAllUnits(side);
    }
  }

  function grantDodge(side: Side, stacks: number, sourceInstanceId: string | undefined, simTime: number) {
    const pool = pools[side];
    const before = pool.dodgeStacks;
    pool.dodgeStacks = clamp(pool.dodgeStacks + stacks, 0, MAX_DODGE_STACKS);
    if (pool.dodgeStacks !== before) log.push({ simTime, type: 'team_pool_stat_applied', side, stat: 'dodge', amount: pool.dodgeStacks - before, total: pool.dodgeStacks, sourceInstanceId });
  }

  function shredDodge(side: Side, stacks: number, simTime: number) {
    const pool = pools[side];
    const before = pool.dodgeStacks;
    pool.dodgeStacks = clamp(pool.dodgeStacks - stacks, 0, MAX_DODGE_STACKS);
    if (pool.dodgeStacks !== before) log.push({ simTime, type: 'team_pool_stat_applied', side, stat: 'dodge', amount: pool.dodgeStacks - before, total: pool.dodgeStacks });
  }

  function shredThorns(side: Side, percent: number, simTime: number) {
    const pool = pools[side];
    const before = pool.thornsPercent;
    pool.thornsPercent = clamp(pool.thornsPercent - percent, 0, MAX_THORNS_PERCENT);
    if (pool.thornsPercent !== before) log.push({ simTime, type: 'team_pool_stat_applied', side, stat: 'thorns', amount: pool.thornsPercent - before, total: pool.thornsPercent });
  }

  function grantFragility(side: Side, percent: number, sourceInstanceId: string | undefined, simTime: number) {
    const pool = pools[side];
    const before = pool.fragilityPercent;
    pool.fragilityPercent = clamp(pool.fragilityPercent + percent, 0, MAX_FRAGILITY_PERCENT);
    if (pool.fragilityPercent !== before) log.push({ simTime, type: 'team_pool_stat_applied', side, stat: 'fragility', amount: pool.fragilityPercent - before, total: pool.fragilityPercent, sourceInstanceId });
  }

  function grantThorns(side: Side, percent: number, sourceInstanceId: string | undefined, simTime: number) {
    const pool = pools[side];
    const before = pool.thornsPercent;
    pool.thornsPercent = clamp(pool.thornsPercent + percent, 0, MAX_THORNS_PERCENT);
    if (pool.thornsPercent !== before) log.push({ simTime, type: 'team_pool_stat_applied', side, stat: 'thorns', amount: pool.thornsPercent - before, total: pool.thornsPercent, sourceInstanceId });
  }

  function grantVampirism(side: Side, percent: number, sourceInstanceId: string | undefined, simTime: number) {
    const pool = pools[side];
    const before = pool.vampirismPercent;
    pool.vampirismPercent = clamp(pool.vampirismPercent + percent, 0, MAX_VAMPIRISM_PERCENT);
    if (pool.vampirismPercent !== before) {
      log.push({ simTime, type: 'team_pool_stat_applied', side, stat: 'vampirism', amount: pool.vampirismPercent - before, total: pool.vampirismPercent, sourceInstanceId });
    }
  }

  function shredVampirism(side: Side, percent: number, simTime: number) {
    const pool = pools[side];
    const before = pool.vampirismPercent;
    pool.vampirismPercent = clamp(pool.vampirismPercent - percent, 0, MAX_VAMPIRISM_PERCENT);
    if (pool.vampirismPercent !== before) log.push({ simTime, type: 'team_pool_stat_applied', side, stat: 'vampirism', amount: pool.vampirismPercent - before, total: pool.vampirismPercent });
  }

  function stripPositiveEnemyStatuses(side: Side, amount: number, simTime: number): number {
    const pool = pools[side];
    const before = pool.shield + pool.hasteStacks + pool.dodgeStacks + pool.thornsPercent + pool.vampirismPercent;
    removeShield(side, amount, simTime);
    shredHaste(side, amount, simTime);
    shredDodge(side, amount, simTime);
    shredThorns(side, amount, simTime);
    shredVampirism(side, amount, simTime);
    const after = pool.shield + pool.hasteStacks + pool.dodgeStacks + pool.thornsPercent + pool.vampirismPercent;
    return before - after;
  }

  function grantExecutionMark(side: Side, stacks: number, sourceInstanceId: string | undefined, simTime: number) {
    const pool = pools[side];
    const before = pool.executionStacks;
    pool.executionStacks = clamp(pool.executionStacks + stacks, 0, MAX_EXECUTION_STACKS);
    if (pool.executionStacks !== before) {
      log.push({ simTime, type: 'team_pool_stat_applied', side, stat: 'execution', amount: pool.executionStacks - before, total: pool.executionStacks, sourceInstanceId });
      checkExecution(side, simTime);
    }
  }

  function stealBuff(casterSide: Side, buff: 'haste' | 'dodge' | 'shield', percent: number, simTime: number) {
    const enemySide = otherSide(casterSide);
    const enemyPool = pools[enemySide];
    if (buff === 'haste') {
      const amount = enemyPool.hasteStacks * (percent / 100);
      if (amount <= 0) return;
      shredHaste(enemySide, amount, simTime);
      grantHaste(casterSide, amount, undefined, simTime);
    } else if (buff === 'dodge') {
      const amount = enemyPool.dodgeStacks * (percent / 100);
      if (amount <= 0) return;
      shredDodge(enemySide, amount, simTime);
      grantDodge(casterSide, amount, undefined, simTime);
    } else {
      const amount = enemyPool.shield * (percent / 100);
      if (amount <= 0) return;
      const removed = removeShield(enemySide, amount, simTime);
      if (removed > 0) applyShieldToPool(casterSide, removed, undefined, simTime);
    }
  }

  function buffAttack(unit: RuntimeUnit, percent: number, sourceInstanceId: string | undefined, simTime: number) {
    unit.attackDamageBonusPercent = clamp(unit.attackDamageBonusPercent + percent, -MAX_WEAKEN_PERCENT, MAX_ATTACK_BUFF_PERCENT);
    recomputeDerivedStats(unit, pools[unit.side]);
    log.push({ simTime, type: 'unit_buff_applied', instanceId: unit.instanceId, stat: 'attack', percent, sourceInstanceId });
  }

  function buffAttackSpeed(unit: RuntimeUnit, percent: number, sourceInstanceId: string | undefined, simTime: number) {
    if (unit.baseAttackIntervalSec === null) return;
    unit.attackSpeedBonusPercent = clamp(unit.attackSpeedBonusPercent + percent, -MAX_SLOW_PERCENT, MAX_HASTE_PERCENT);
    recomputeDerivedStats(unit, pools[unit.side]);
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

  function isAdjacentPosition(a: BoardPosition, b: BoardPosition): boolean {
    return !(a.row === b.row && a.col === b.col) && Math.abs(a.row - b.row) <= 1 && Math.abs(a.col - b.col) <= 1;
  }

  /**
   * Applies one effect as if cast from `side`. `excludeUnit`, when given, is
   * skipped by team-wide effects (a unit's own team-wide buff hits every
   * OTHER ally, not itself) — omitted entirely for augments, which have no
   * single caster and so affect the whole side uniformly. `tagFilter`
   * (augments only) restricts team-wide/enemy-wide/per-unit-passive effects
   * to units carrying one of those tags. Pure pool-level effects (haste,
   * dodge, shield, fragility, thorns, execution, momentum, reactions) ignore
   * both `excludeUnit` and `tagFilter` — a status on the shared pool has no
   * per-unit meaning to exclude or filter.
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
        applyShieldToPool(side, effect.amount, sourceInstanceId, simTime);
        break;
      case 'shield_gain_bonus_own_pool':
        pools[side].shieldGainBonusFlat += effect.amount;
        break;
      case 'poison_enemy_pool':
        applyPoisonToPool(otherSide(side), effect.damagePerSec, sourceInstanceId, simTime);
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
      case 'buff_team_attack_speed_per_adjacent_ally': {
        if (!excludeUnit) break;
        const adjacentCount = units.filter(
          (u) => u.side === side && u !== excludeUnit && isAdjacentPosition(u.position, excludeUnit.position) && hasAnyTag(u, effect.tagFilter),
        ).length;
        const totalPercent = adjacentCount * effect.percentPerAlly;
        if (totalPercent > 0) {
          for (const ally of units) if (ally.side === side && ally !== excludeUnit) buffAttackSpeed(ally, totalPercent, sourceInstanceId, simTime);
        }
        break;
      }
      case 'haste_stacks_per_adjacent_ally': {
        if (!excludeUnit) break;
        const adjacentCount = units.filter(
          (u) => u.side === side && u !== excludeUnit && isAdjacentPosition(u.position, excludeUnit.position) && hasAnyTag(u, effect.tagFilter),
        ).length;
        if (adjacentCount > 0) grantHaste(side, adjacentCount * effect.stacksPerAlly, sourceInstanceId, simTime);
        break;
      }
      case 'weaken_enemy_team_attack':
        for (const foe of units) if (foe.side === otherSide(side) && hasAnyTag(foe, tagFilter)) buffAttack(foe, -effect.percent, sourceInstanceId, simTime);
        break;
      case 'slow_enemy_team_attack_speed':
        for (const foe of units) if (foe.side === otherSide(side) && hasAnyTag(foe, tagFilter)) buffAttackSpeed(foe, -effect.percent, sourceInstanceId, simTime);
        break;
      case 'slow_enemy_pool':
        grantSlow(otherSide(side), effect.percent, sourceInstanceId, simTime);
        break;
      case 'weaken_enemy_pool':
        grantWeaken(otherSide(side), effect.percent, sourceInstanceId, simTime);
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
        {
          const pool = pools[side];
          const removed = pool.poisonDamagePerSec;
          pool.poisonDamagePerSec = 0;
          if (removed > 0) log.push({ simTime, type: 'team_pool_poison_changed', side, amount: -removed, total: 0, sourceInstanceId });
        }
        break;
      case 'shred_enemy_shield': {
        const enemyPool = pools[otherSide(side)];
        enemyPool.shield = Math.max(0, enemyPool.shield - effect.amount);
        break;
      }
      case 'shred_all_enemy_buffs': {
        const enemySide = otherSide(side);
        stripPositiveEnemyStatuses(enemySide, effect.amount, simTime);
        break;
      }
      case 'shred_all_enemy_buffs_and_poison': {
        const enemySide = otherSide(side);
        const removed = stripPositiveEnemyStatuses(enemySide, effect.amount, simTime);
        if (removed > 0) applyPoisonToPool(enemySide, effect.poisonDamagePerSec, sourceInstanceId, simTime);
        break;
      }
      case 'haste_stacks_own_pool':
        grantHaste(side, effect.stacks, sourceInstanceId, simTime);
        break;
      case 'strength_stacks_own_pool':
        grantStrength(side, effect.stacks, sourceInstanceId, simTime);
        break;
      case 'random_team_buff': {
        const option = effect.options[Math.floor(rng() * effect.options.length)];
        if (option.kind === 'strength') grantStrength(side, option.stacks, sourceInstanceId, simTime);
        else if (option.kind === 'haste') grantHaste(side, option.stacks, sourceInstanceId, simTime);
        else if (option.kind === 'dodge') grantDodge(side, option.stacks, sourceInstanceId, simTime);
        else if (option.kind === 'vampirism') grantVampirism(side, option.stacks, sourceInstanceId, simTime);
        else applyShieldToPool(side, option.amount, sourceInstanceId, simTime);
        break;
      }
      case 'damage_enemy_pool_scaled_by_own_haste': {
        const bonus = pools[side].hasteStacks * effect.multiplier;
        if (bonus > 0) applyDamageToPool(otherSide(side), bonus, 'ability', sourceInstanceId, simTime);
        break;
      }
      case 'damage_enemy_pool_scaled_by_enemy_slow': {
        const bonus = pools[otherSide(side)].slowPercent * effect.multiplier;
        if (bonus > 0) applyDamageToPool(otherSide(side), bonus, 'ability', sourceInstanceId, simTime);
        break;
      }
      case 'damage_enemy_pool_scaled_by_enemy_poison': {
        const bonus = pools[otherSide(side)].poisonDamagePerSec * effect.multiplier;
        if (bonus > 0) applyDamageToPool(otherSide(side), bonus, 'ability', sourceInstanceId, simTime);
        break;
      }
      case 'dodge_stacks_own_pool':
        grantDodge(side, effect.stacks, sourceInstanceId, simTime);
        break;
      case 'fragility_enemy_pool':
        grantFragility(otherSide(side), effect.percent, sourceInstanceId, simTime);
        break;
      case 'thorns_own_pool':
        grantThorns(side, effect.percent, sourceInstanceId, simTime);
        break;
      case 'vampirism_stacks_own_pool':
        grantVampirism(side, effect.stacks, sourceInstanceId, simTime);
        break;
      case 'execution_mark_enemy_pool':
        grantExecutionMark(otherSide(side), effect.stacks, sourceInstanceId, simTime);
        break;
      case 'execution_empower_enemy_pool': {
        const enemyPool = pools[otherSide(side)];
        enemyPool.executionHpThreshold = clamp(enemyPool.executionHpThreshold + effect.hpThresholdBonus, 0, MAX_EXECUTION_HP_THRESHOLD);
        enemyPool.executionStacksRequired = Math.max(1, enemyPool.executionStacksRequired - effect.stacksRequiredReduction);
        break;
      }
      case 'reduce_own_shield_gain':
        pools[side].shieldGainReductionPercent = Math.min(100, pools[side].shieldGainReductionPercent + effect.percent);
        break;
      case 'shred_enemy_haste_stacks':
        shredHaste(otherSide(side), effect.stacks, simTime);
        break;
      case 'shred_and_grant_haste':
        shredHaste(otherSide(side), effect.shredStacks, simTime);
        grantHaste(side, effect.grantStacks, sourceInstanceId, simTime);
        break;
      case 'shred_enemy_dodge_stacks':
        shredDodge(otherSide(side), effect.stacks, simTime);
        break;
      case 'shred_dodge_on_hit_team':
        for (const ally of units) {
          if (ally.side === side && hasAnyTag(ally, tagFilter)) ally.shredDodgeOnHitStacks = Math.min(MAX_SHRED_ON_HIT_STACKS, ally.shredDodgeOnHitStacks + effect.stacks);
        }
        break;
      case 'execution_mark_on_hit_team':
        for (const ally of units) {
          if (ally.side === side && hasAnyTag(ally, tagFilter)) ally.executionMarkOnHitStacks = Math.min(MAX_SHRED_ON_HIT_STACKS, ally.executionMarkOnHitStacks + effect.stacks);
        }
        break;
      case 'steal_buff':
        stealBuff(side, effect.buff, effect.percent, simTime);
        break;
      case 'multicast_team':
        for (const ally of units) {
          if (ally.side === side && hasAnyTag(ally, tagFilter)) {
            ally.multicastExtraHits = Math.min(MAX_MULTICAST_EXTRA_HITS, ally.multicastExtraHits + effect.extraHits);
            ally.multicastExtraHitPercent = Math.max(ally.multicastExtraHitPercent, effect.extraHitPercent);
          }
        }
        break;
      case 'multicast_team_per_unique_unit': {
        const uniqueUnitCount = new Set(units.filter((ally) => ally.side === side).map((ally) => ally.unitId)).size;
        for (const ally of units) {
          if (ally.side === side && hasAnyTag(ally, effect.tagFilter)) {
            ally.multicastExtraHits = Math.min(MAX_MULTICAST_EXTRA_HITS, ally.multicastExtraHits + uniqueUnitCount);
            ally.multicastExtraHitPercent = Math.max(ally.multicastExtraHitPercent, effect.extraHitPercent);
          }
        }
        break;
      }
      case 'momentum_own_pool': {
        const pool = pools[side];
        pool.momentumHasteStacksPerSec += effect.hasteStacksPerSec;
        pool.momentumAttackPercentPerSec += effect.attackPercentPerSec;
        break;
      }
      case 'reaction_on_shield_gained':
        pools[side].reactions.push({ on: 'shield_gained', effect: effect.reaction });
        break;
      case 'reaction_on_shield_depleted':
        pools[side].reactions.push({ on: 'shield_depleted', effect: effect.reaction });
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
    positionalBonusesApplied: positionalModsBySide[u.side][u.instanceId]?.appliedBonusIds ?? [],
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
  for (const unit of units) {
    if (unit.strengthStacks > 0) {
      log.push({ simTime: 0, type: 'unit_buff_applied', instanceId: unit.instanceId, stat: 'strength', percent: unit.strengthStacks });
    }
  }
  log.push({ simTime: 0, type: 'start' });

  for (const unit of units) {
    for (const ability of unit.startOfCombatAbilities) {
      triggerAbility(unit, ability, 0);
    }
  }

  // Augment effects apply in three passes, so authored order inside one
  // augment's `effects` array (or pick order between the two sides) never
  // matters for correctness:
  //   1. reaction_on_* registrations — armed before anything that could
  //      fire them, so "shield 30 + react-on-shield-gained" in that exact
  //      order still catches its own shield grant.
  //   2. everything else.
  //   3. steal_buff — always sees the opponent's fully-applied starting
  //      stacks/shield.
  const pendingAugments: Array<{ side: Side; effect: AbilityEffect; tagFilter?: string[] }> = [
    ...(input.player.augmentEffects ?? []).map((a) => ({ side: 'player' as Side, ...a })),
    ...(input.enemy.augmentEffects ?? []).map((a) => ({ side: 'enemy' as Side, ...a })),
  ];
  const isReaction = (k: AbilityEffect['kind']) => k === 'reaction_on_shield_gained' || k === 'reaction_on_shield_depleted';
  for (const a of pendingAugments) if (isReaction(a.effect.kind)) applyEffectFromSide(a.side, a.effect, 0, undefined, a.tagFilter);
  for (const a of pendingAugments) if (!isReaction(a.effect.kind) && a.effect.kind !== 'steal_buff') applyEffectFromSide(a.side, a.effect, 0, undefined, a.tagFilter);
  for (const a of pendingAugments) if (a.effect.kind === 'steal_buff') applyEffectFromSide(a.side, a.effect, 0, undefined, a.tagFilter);

  let winner: Side | null = null;
  let simTime = 0;

  function fireAttack(unit: RuntimeUnit, def: UnitDef, atSimTime: number, isMulticastHit: boolean) {
    log.push({ simTime: atSimTime, type: 'unit_attack_fired', instanceId: unit.instanceId, emoji: def.emoji, multicast: isMulticastHit || undefined });
    const damage = isMulticastHit ? unit.attackDamage * (unit.multicastExtraHitPercent / 100) : unit.attackDamage;
    if (damage > 0) {
      applyDamageToPool(otherSide(unit.side), damage, 'attack', unit.instanceId, atSimTime);
      if (unit.shredDodgeOnHitStacks > 0) shredDodge(otherSide(unit.side), unit.shredDodgeOnHitStacks, atSimTime);
      if (unit.executionMarkOnHitStacks > 0) grantExecutionMark(otherSide(unit.side), unit.executionMarkOnHitStacks, unit.instanceId, atSimTime);
    }
  }

  while (simTime < timeoutSec) {
    for (const unit of units) {
      const def = input.unitDefs[unit.unitId];

      if (unit.attackIntervalSec !== null && simTime - unit.lastAttackAt >= unit.attackIntervalSec) {
        unit.lastAttackAt = simTime;
        fireAttack(unit, def, simTime, false);

        for (const ability of unit.onTriggerAbilities) {
          if (ability.trigger === 'on_trigger') triggerAbility(unit, ability, simTime);
        }

        if (unit.shieldOnTriggerAmount > 0) {
          applyShieldToPool(unit.side, unit.shieldOnTriggerAmount, unit.instanceId, simTime);
        }

        if (unit.slowOnAttackPercent > 0) {
          applyEffectFromSide(unit.side, { kind: 'slow_enemy_pool', percent: unit.slowOnAttackPercent }, simTime, unit);
        }

        if (unit.attackDamage > 0 && unit.multicastExtraHits > 0) {
          for (let i = 0; i < unit.multicastExtraHits; i++) {
            fireAttack(unit, def, simTime + (i + 1) * MULTICAST_HIT_DELAY_SEC, true);
          }
        }
      }

      for (const ability of unit.onTriggerAbilities) {
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
      if (pool.poisonDamagePerSec > 0 && simTime - pool.lastPoisonTickAt >= 1) {
        pool.lastPoisonTickAt = simTime;
        applyPoisonTick(side, pool.poisonDamagePerSec, simTime);
      }
      if (pool.regenPerSec > 0 && simTime - pool.lastRegenTickAt >= 1) {
        pool.lastRegenTickAt = simTime;
        applyHealToPool(side, pool.regenPerSec, undefined, simTime);
      }
      if ((pool.momentumHasteStacksPerSec > 0 || pool.momentumAttackPercentPerSec > 0) && simTime - pool.lastMomentumTickAt >= 1) {
        pool.lastMomentumTickAt = simTime;
        if (pool.momentumHasteStacksPerSec > 0) grantHaste(side, pool.momentumHasteStacksPerSec, undefined, simTime);
        if (pool.momentumAttackPercentPerSec > 0) {
          for (const ally of units) if (ally.side === side) buffAttack(ally, pool.momentumAttackPercentPerSec, undefined, simTime);
        }
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
