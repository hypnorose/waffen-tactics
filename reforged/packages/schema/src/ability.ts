import { z } from 'zod';

// MVP trigger taxonomy — see plan decision #5. on_kill / on_bonus_attack have
// no equivalent in Reforged (no individual death, no bonus-attack layer).
// `on_attack` fires whenever a unit's own action cadence (1/attacksPerSecond)
// elapses — this is true whether or not the unit actually deals damage, so a
// unit with attacksPerSecond but no attack stat still triggers on_attack
// abilities on schedule (e.g. "cast a buff every cooldown" support units).
export const AbilityTriggerSchema = z.enum(['start_of_combat', 'on_attack', 'periodic', 'low_team_hp']);
export type AbilityTrigger = z.infer<typeof AbilityTriggerSchema>;

// The handful of things a shield/haste/dodge/damage "reaction" is allowed to
// grant — intentionally a small, flat, non-recursive union (not the full
// AbilityEffect set) so reaction chains can't nest reactions inside
// reactions and can't reference anything with per-unit meaning.
export const ReactionEffectSchema = z.discriminatedUnion('kind', [
  z.object({ kind: z.literal('grant_haste_stacks'), stacks: z.number().positive() }),
  z.object({ kind: z.literal('grant_dodge_stacks'), stacks: z.number().positive() }),
  z.object({ kind: z.literal('grant_shield'), amount: z.number().positive() }),
  z.object({ kind: z.literal('damage_enemy_pool'), amount: z.number().positive() }),
  z.object({ kind: z.literal('buff_team_attack'), percent: z.number().positive() }),
]);
export type ReactionEffect = z.infer<typeof ReactionEffectSchema>;

export const AbilityEffectSchema = z.discriminatedUnion('kind', [
  z.object({ kind: z.literal('damage_enemy_pool'), amount: z.number().positive() }),
  z.object({ kind: z.literal('heal_own_pool'), amount: z.number().positive() }),
  // No decay — a shield is a flat absorb-then-gone buffer, permanent until
  // consumed by damage. It never disappears on its own.
  z.object({ kind: z.literal('shield_own_pool'), amount: z.number().positive() }),
  // Ticking damage on the enemy pool — stacks additively with every other
  // active poison source, ticks once per second independent of anyone's
  // attack cadence. Bypasses both shield and dodge (see combat-engine):
  // poison is a status, not an attack instance, so nothing that blocks or
  // absorbs a hit blocks it. See combat-engine's MAX_POISON_DPS for the cap.
  z.object({ kind: z.literal('poison_enemy_pool'), damagePerSec: z.number().positive() }),
  // Mirror of poison_enemy_pool, but healing your own pool — a persistent
  // "regen" status instead of an instant heal. Prefer this over
  // heal_own_pool on start_of_combat: an instant heal at t=0 reads as a
  // bigger max-HP number, while regen is a genuinely different status effect
  // (keeps paying off for as long as the fight runs). Stacks additively with
  // every other active regen source — see MAX_REGEN_PER_SEC for the cap.
  z.object({ kind: z.literal('regen_own_pool'), amountPerSec: z.number().positive() }),
  // Self-only: modifies only the triggering unit's own attack/speed. Stacks
  // are additive and clamped — see combat-engine's MAX_*_PERCENT constants
  // ("haste"/buff stacking needs a ceiling, or a support firing every
  // cooldown for 120s would break the game).
  z.object({ kind: z.literal('buff_attack'), percent: z.number() }),
  z.object({ kind: z.literal('buff_attack_speed'), percent: z.number() }),
  // Team-wide flat attack%, per-unit event (unchanged legacy path — still
  // the right tool for a plain damage buff). Speed buffs on augments should
  // prefer haste_stacks_own_pool instead (see below); this is kept for unit
  // abilities and existing content.
  z.object({ kind: z.literal('buff_team_attack'), percent: z.number() }),
  z.object({ kind: z.literal('buff_team_attack_speed'), percent: z.number() }),
  z.object({ kind: z.literal('weaken_enemy_team_attack'), percent: z.number().positive() }),
  z.object({ kind: z.literal('slow_enemy_team_attack_speed'), percent: z.number().positive() }),
  // Damage scaled to the enemy's CURRENT pool, not a flat amount — hits
  // harder the longer the fight drags on instead of a fixed number.
  z.object({ kind: z.literal('execute_enemy_pool'), percentOfCurrentHp: z.number().positive() }),
  // Heals the caster's own pool by a percentage of the damage its own attack
  // just dealt — on_attack only, scales with the unit's own power instead of
  // a fixed heal amount.
  z.object({ kind: z.literal('lifesteal_own_pool'), percent: z.number().positive() }),
  // Utility, not a number: wipes any active poison currently ticking on the
  // caster's own side.
  z.object({ kind: z.literal('cleanse_own_pool') }),
  // Anti-shield counterplay: strips a flat amount off the enemy's current
  // shield (does nothing if they have none up) — a one-shot chunk, unlike
  // shred_enemy_haste_stacks/shred_enemy_dodge_stacks below which target the
  // other two team-pool statuses.
  z.object({ kind: z.literal('shred_enemy_shield'), amount: z.number().positive() }),

  // --- Team-pool statuses. All of these live on the shared pool, not on
  // individual units — see the design note at the top of augments.ts. ---

  // 1 stack = 1% attack speed for every unit on the side, uncapped input but
  // clamped team-wide at MAX_HASTE_STACKS.
  z.object({ kind: z.literal('haste_stacks_own_pool'), stacks: z.number().positive() }),
  // 1 stack = 1% chance to fully negate an incoming attack/ability hit
  // (poison excluded — see above), clamped team-wide at MAX_DODGE_STACKS
  // (70).
  z.object({ kind: z.literal('dodge_stacks_own_pool'), stacks: z.number().positive() }),
  // Kruchość: the enemy pool takes this many % MORE damage from every
  // source, including poison — a multiplier on top of mitigation, not a
  // mitigation itself.
  z.object({ kind: z.literal('fragility_enemy_pool'), percent: z.number().positive() }),
  // Kolce: whenever the own pool's HP (not shield) is reduced by an attack
  // or ability, this % of that HP loss is dealt back to the enemy pool.
  // Reflected damage never itself re-triggers thorns (no infinite chains).
  z.object({ kind: z.literal('thorns_own_pool'), percent: z.number().positive() }),
  // Egzekucja: marks the enemy pool. See execution_empower_enemy_pool for
  // the two knobs (HP threshold, stacks required) that decide when marks
  // actually kill — a pool with marks but no augment that lowered the
  // requirement just sits there inert.
  z.object({ kind: z.literal('execution_mark_enemy_pool'), stacks: z.number().positive() }),
  z.object({
    kind: z.literal('execution_empower_enemy_pool'),
    hpThresholdPercentBonus: z.number().nonnegative().default(0),
    stacksRequiredReduction: z.number().nonnegative().default(0),
  }),
  // Persistent, own-side debuff: every future shield_own_pool grant (any
  // source, including steal_buff landing on this side) is reduced by this
  // %. Stacks additively across sources.
  z.object({ kind: z.literal('reduce_own_shield_gain'), percent: z.number().positive().max(100) }),
  z.object({ kind: z.literal('shred_enemy_haste_stacks'), stacks: z.number().positive() }),
  z.object({ kind: z.literal('shred_enemy_dodge_stacks'), stacks: z.number().positive() }),
  // Per-unit passive granted team-wide (or tag-filtered, via the augment's
  // own tagFilter): every landed attack from an affected unit shreds this
  // many dodge stacks off the enemy pool.
  z.object({ kind: z.literal('shred_dodge_on_hit_team'), stacks: z.number().positive() }),
  // Per-unit passive granted team-wide (or tag-filtered): every landed
  // attack from an affected unit also marks the enemy pool with this many
  // execution stacks.
  z.object({ kind: z.literal('execution_mark_on_hit_team'), stacks: z.number().positive() }),
  // Transfers (not copies) a % of the enemy's CURRENT value of the named
  // buff to the caster's own side. Resolved in a dedicated pass after every
  // non-steal augment effect has applied (see engine.ts), so it isn't
  // order-dependent on pick order.
  z.object({ kind: z.literal('steal_buff'), buff: z.enum(['haste', 'dodge', 'shield']), percent: z.number().positive().max(100) }),
  // Per-unit passive granted team-wide (or tag-filtered): every normal
  // attack fires `extraHits` additional hits right after the first, each
  // dealing extraHitPercent% of the unit's own attack damage (not the
  // primary hit's damage), spaced a fraction of a second apart.
  z.object({
    kind: z.literal('multicast_team'),
    extraHits: z.number().int().min(1).max(3),
    extraHitPercent: z.number().positive().max(100),
  }),
  // Every second: grants this many haste stacks and this much flat team
  // attack% (both optional/independent), uncapped duration — keeps paying
  // out for as long as the fight runs.
  z.object({
    kind: z.literal('momentum_own_pool'),
    hasteStacksPerSec: z.number().nonnegative().default(0),
    attackPercentPerSec: z.number().nonnegative().default(0),
  }),
  // Fires `reaction` once, every time the own pool's shield goes from 0 to
  // >0 (any source, including this same augment's own shield_own_pool —
  // reaction registrations always resolve before any other augment effect,
  // so authored order inside one augment's effects array doesn't matter).
  z.object({ kind: z.literal('reaction_on_shield_gained'), reaction: ReactionEffectSchema }),
  // Fires `reaction` once, every time the own pool's shield is fully
  // consumed down to exactly 0 by damage.
  z.object({ kind: z.literal('reaction_on_shield_depleted'), reaction: ReactionEffectSchema }),
]);
export type AbilityEffect = z.infer<typeof AbilityEffectSchema>;

export const AbilitySchema = z
  .object({
    id: z.string(),
    trigger: AbilityTriggerSchema,
    periodSec: z.number().positive().optional(),
    hpThresholdPercent: z.number().min(0).max(1).optional(),
    effect: AbilityEffectSchema,
    description: z.string(),
  })
  .refine((ability) => ability.trigger !== 'periodic' || ability.periodSec !== undefined, {
    message: 'periodic abilities require periodSec',
    path: ['periodSec'],
  })
  .refine((ability) => ability.trigger !== 'low_team_hp' || ability.hpThresholdPercent !== undefined, {
    message: 'low_team_hp abilities require hpThresholdPercent',
    path: ['hpThresholdPercent'],
  });
export type Ability = z.infer<typeof AbilitySchema>;
