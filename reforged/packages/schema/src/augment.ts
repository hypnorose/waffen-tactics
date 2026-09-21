import { z } from 'zod';
import { AbilityEffectSchema } from './ability.js';
import { AugmentTierSchema } from './run.js';

export const AugmentDefSchema = z.object({
  id: z.string(),
  name: z.string(),
  tier: AugmentTierSchema,
  description: z.string(),
  effect: AbilityEffectSchema,
});
export type AugmentDef = z.infer<typeof AugmentDefSchema>;
