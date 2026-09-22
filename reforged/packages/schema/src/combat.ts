import { z } from 'zod';
import { BoardPositionSchema } from './board.js';

export const SideSchema = z.enum(['player', 'enemy']);
export type Side = z.infer<typeof SideSchema>;

// One shared HP pool per team — units never die individually, they attack for
// the whole fight; only the pool determines the win condition. See plan decision
// "wspólne HP drużyny".
export const TeamPoolStateSchema = z.object({
  side: SideSchema,
  hpMax: z.number().positive(),
  hpCurrent: z.number(),
  shield: z.number().nonnegative().default(0),
  // 1 stack = 1% — see ability.ts's haste_stacks_own_pool / dodge_stacks_own_pool.
  hasteStacks: z.number().nonnegative().default(0),
  dodgeStacks: z.number().nonnegative().default(0),
  // % more damage taken (kruchość) / % of own HP loss reflected (kolce).
  fragilityPercent: z.number().nonnegative().default(0),
  thornsPercent: z.number().nonnegative().default(0),
  // Egzekucja marks carried by this pool — see execution_mark_enemy_pool.
  executionStacks: z.number().nonnegative().default(0),
});
export type TeamPoolState = z.infer<typeof TeamPoolStateSchema>;

export const UnitCombatStateSchema = z.object({
  instanceId: z.string(),
  unitId: z.string(),
  side: SideSchema,
  position: BoardPositionSchema,
  attackIntervalSec: z.number().positive().nullable(), // null = this unit never attacks/acts on a cadence
  lastAttackAt: z.number().nonnegative(),
  abilityCooldowns: z.record(z.string(), z.number()),
  positionalBonusesApplied: z.array(z.string()),
  // 1 = normal ability cadence, 2 = an active positional same-trait synergy.
  triggerMultiplier: z.number().int().min(1).max(2),
});
export type UnitCombatState = z.infer<typeof UnitCombatStateSchema>;

const baseEventFields = {
  seq: z.number().int().nonnegative(),
  simTime: z.number().nonnegative(),
};

// No targeting fields anywhere in this log — a direct consequence of shared-pool
// HP. Attacks/abilities only ever touch "own pool" or "enemy pool", never a
// specific enemy unit. See plan decision #4.
export const CombatEventSchema = z.discriminatedUnion('type', [
  z.object({
    ...baseEventFields,
    type: z.literal('units_init'),
    player: z.array(UnitCombatStateSchema),
    enemy: z.array(UnitCombatStateSchema),
    playerHpMax: z.number().positive(),
    enemyHpMax: z.number().positive(),
  }),
  z.object({ ...baseEventFields, type: z.literal('start') }),
  z.object({
    ...baseEventFields,
    type: z.literal('unit_attack_fired'),
    instanceId: z.string(),
    emoji: z.string(),
    // Set on the extra hits a multicast_team passive adds after the primary
    // hit of the same attack cycle — lets the UI render them as a quick
    // flurry instead of a second full attack.
    multicast: z.boolean().optional(),
  }),
  z.object({
    ...baseEventFields,
    type: z.literal('team_pool_damage'),
    side: SideSchema,
    amount: z.number().positive(),
    postHp: z.number(),
    cause: z.enum(['attack', 'ability']),
    sourceInstanceId: z.string().optional(),
  }),
  z.object({
    ...baseEventFields,
    type: z.literal('team_pool_heal'),
    side: SideSchema,
    amount: z.number().positive(),
    postHp: z.number(),
    sourceInstanceId: z.string().optional(),
  }),
  z.object({
    ...baseEventFields,
    type: z.literal('team_pool_shield_applied'),
    side: SideSchema,
    // Negative = shield removed by steal_buff landing on the victim side —
    // every other source only ever grants (positive).
    amount: z.number(),
    sourceInstanceId: z.string().optional(),
  }),
  z.object({
    ...baseEventFields,
    type: z.literal('ability_triggered'),
    instanceId: z.string(),
    abilityId: z.string(),
    trigger: z.string(),
  }),
  // Drives the "buff/debuff icon under the unit" UI — percent is signed
  // (negative = a slow/weaken-style debuff, if content ever adds one).
  z.object({
    ...baseEventFields,
    type: z.literal('unit_buff_applied'),
    instanceId: z.string(),
    stat: z.enum(['attack', 'attackSpeed']),
    percent: z.number(),
    sourceInstanceId: z.string().optional(),
  }),
  // One shared event for every team-pool status stack change (haste, dodge,
  // fragility, thorns, execution marks) — `total` is the post-change value,
  // so the UI never needs to sum deltas itself.
  z.object({
    ...baseEventFields,
    type: z.literal('team_pool_stat_applied'),
    side: SideSchema,
    stat: z.enum(['haste', 'dodge', 'fragility', 'thorns', 'execution']),
    amount: z.number(),
    total: z.number(),
    sourceInstanceId: z.string().optional(),
  }),
  // A dodge_stacks_own_pool roll fully negated an incoming hit — no damage
  // event follows for that hit.
  z.object({
    ...baseEventFields,
    type: z.literal('team_pool_dodge_proc'),
    side: SideSchema,
    negatedAmount: z.number().positive(),
  }),
  // Egzekucja condition met: this pool's HP was set straight to 0, bypassing
  // shield/dodge/fragility entirely — the fight ends right after this event.
  z.object({ ...baseEventFields, type: z.literal('team_pool_executed'), side: SideSchema }),
  z.object({ ...baseEventFields, type: z.literal('victory'), winner: SideSchema }),
  z.object({ ...baseEventFields, type: z.literal('end') }),
]);
export type CombatEvent = z.infer<typeof CombatEventSchema>;

export const CombatLogSchema = z.object({
  combatId: z.string(),
  seed: z.number().int(),
  events: z.array(CombatEventSchema),
});
export type CombatLog = z.infer<typeof CombatLogSchema>;
