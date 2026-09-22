import { z } from 'zod';

// MVP trigger taxonomy — see plan decision #5. on_kill / on_bonus_attack have
// no equivalent in Reforged (no individual death, no bonus-attack layer).
// `on_attack` fires whenever a unit's own action cadence (1/attacksPerSecond)
// elapses — this is true whether or not the unit actually deals damage, so a
// unit with attacksPerSecond but no attack stat still triggers on_attack
// abilities on schedule (e.g. "cast a buff every cooldown" support units).
export const AbilityTriggerSchema = z.enum(['start_of_combat', 'on_attack', 'periodic', 'low_team_hp']);
export type AbilityTrigger = z.infer<typeof AbilityTriggerSchema>;

export const AbilityEffectSchema = z.discriminatedUnion('kind', [
  z.object({ kind: z.literal('damage_enemy_pool'), amount: z.number().positive() }),
  z.object({ kind: z.literal('heal_own_pool'), amount: z.number().positive() }),
  z.object({
    kind: z.literal('shield_own_pool'),
    amount: z.number().positive(),
    // Shields aren't permanent — they decay by this % of their current value
    // every second until consumed by damage or fully decayed. Omit for a
    // flat non-decaying shield (e.g. a one-time start-of-combat cushion).
    decayPercentPerSec: z.number().min(0).max(100).optional(),
  }),
  // Ticking damage on the enemy pool — stacks additively with every other
  // active poison source, ticks once per second independent of anyone's
  // attack cadence. See combat-engine's MAX_POISON_DPS for the stack cap.
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
  // Team-wide: modifies every OTHER allied unit's attack/speed for the rest
  // of the fight. Intentionally stackable — a support unit with no attack of
  // its own can fire this every cooldown, ramping the team up over time
  // (up to the same clamp as the self-only version).
  z.object({ kind: z.literal('buff_team_attack'), percent: z.number() }),
  z.object({ kind: z.literal('buff_team_attack_speed'), percent: z.number() }),
  // Mirror image of the two above, but hits every unit on the OTHER side —
  // "slow"/"weaken" debuffs. `percent` is a positive magnitude (how much to
  // reduce), not a signed delta.
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
  // shield (does nothing if they have none up).
  z.object({ kind: z.literal('shred_enemy_shield'), amount: z.number().positive() }),
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
