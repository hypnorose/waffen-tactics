import { z } from 'zod';

// MVP shapes — see plan decision #6. Diagonal / knight-move shapes deferred.
export const PositionalShapeSchema = z.enum(['self', 'adjacent', 'cross', 'row', 'column']);
export type PositionalShape = z.infer<typeof PositionalShapeSchema>;

// Positional effects deliberately stay separate from regular ability effects.
// A positional bonus can change a unit's stats or grant one deterministic
// trigger synergy, but it must not silently become a second combat ability.
export const PositionalEffectSchema = z.discriminatedUnion('kind', [
  z.object({ kind: z.literal('buff_attack'), percent: z.number() }),
  z.object({ kind: z.literal('buff_attack_speed'), percent: z.number() }),
  z.object({ kind: z.literal('double_trigger') }),
  // Grants every matching ally a passive: on THEIR OWN on_trigger cadence,
  // they also slow the whole enemy team by `percent` — fires whether or not
  // the granted unit deals damage, same as every other on_trigger effect.
  z.object({ kind: z.literal('grant_slow_on_attack'), percent: z.number().positive() }),
  z.object({ kind: z.literal('grant_shield_on_trigger'), amount: z.number().positive() }),
  z.object({ kind: z.literal('grant_strength_stacks'), stacks: z.number().positive() }),
  z.object({
    kind: z.literal('grant_strength_per_adjacent_ally'),
    stacksPerAlly: z.number().positive(),
    maxStacks: z.number().positive(),
  }),
]);
export type PositionalEffect = z.infer<typeof PositionalEffectSchema>;

export const PositionalBonusSchema = z.object({
  id: z.string(),
  shape: PositionalShapeSchema,
  tagFilter: z.array(z.string()).optional(),
  effect: PositionalEffectSchema,
  description: z.string(),
});
export type PositionalBonus = z.infer<typeof PositionalBonusSchema>;
