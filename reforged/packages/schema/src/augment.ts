import { z } from 'zod';
import { AbilityEffectSchema } from './ability.js';
import { AugmentTierSchema } from './run.js';

export const AugmentDefSchema = z.object({
  id: z.string(),
  name: z.string(),
  tier: AugmentTierSchema,
  icon: z.string(),
  description: z.string(),
  // An array (not a single effect) so an augment can be a genuine compound
  // archetype — two different effects together, or the same effect applied
  // twice as a deliberate "double" mechanic — instead of every augment
  // within a tier being the same template with a bigger number.
  effects: z.array(AbilityEffectSchema).min(1),
  // Restricts a team-wide/enemy-wide effect to units carrying one of these
  // tags — lets an augment build toward a tag-based specialization instead
  // of always buffing the whole board uniformly.
  tagFilter: z.array(z.string()).optional(),
  // If set, picking this augment immediately adds a copy of this unit to
  // the run's bench, on top of whatever combat effect it also grants.
  grantUnitId: z.string().optional(),
});
export type AugmentDef = z.infer<typeof AugmentDefSchema>;
