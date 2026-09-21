import { z } from 'zod';

// MVP trigger taxonomy — see plan decision #5. on_kill / on_bonus_attack have
// no equivalent in Reforged (no individual death, no bonus-attack layer).
export const AbilityTriggerSchema = z.enum(['start_of_combat', 'on_attack', 'periodic', 'low_team_hp']);
export type AbilityTrigger = z.infer<typeof AbilityTriggerSchema>;

export const AbilityEffectSchema = z.discriminatedUnion('kind', [
  z.object({ kind: z.literal('damage_enemy_pool'), amount: z.number().positive() }),
  z.object({ kind: z.literal('heal_own_pool'), amount: z.number().positive() }),
  z.object({
    kind: z.literal('shield_own_pool'),
    amount: z.number().positive(),
    durationSec: z.number().positive().optional(),
  }),
  z.object({ kind: z.literal('buff_attack'), percent: z.number() }),
  z.object({ kind: z.literal('buff_attack_speed'), percent: z.number() }),
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
