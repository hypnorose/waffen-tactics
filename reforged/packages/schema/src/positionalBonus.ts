import { z } from 'zod';
import { AbilityEffectSchema } from './ability.js';

// MVP shapes — see plan decision #6. Diagonal / knight-move shapes deferred.
export const PositionalShapeSchema = z.enum(['self', 'adjacent', 'cross', 'row', 'column']);
export type PositionalShape = z.infer<typeof PositionalShapeSchema>;

export const PositionalBonusSchema = z.object({
  id: z.string(),
  shape: PositionalShapeSchema,
  tagFilter: z.array(z.string()).optional(),
  effect: AbilityEffectSchema,
  description: z.string(),
});
export type PositionalBonus = z.infer<typeof PositionalBonusSchema>;
