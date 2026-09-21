import { z } from 'zod';
import { AbilitySchema } from './ability.js';
import { PositionalBonusSchema } from './positionalBonus.js';

// Stats exist only for deterministic simulation — never rendered as raw numbers in the UI.
export const UnitStatsSchema = z.object({
  attack: z.number().positive(),
  attacksPerSecond: z.number().positive(),
  defense: z.number().nonnegative(),
});
export type UnitStats = z.infer<typeof UnitStatsSchema>;

export const UnitDefSchema = z.object({
  id: z.string(),
  name: z.string(),
  cost: z.number().int().min(1).max(5),
  tags: z.array(z.string()).min(1).max(3),
  emoji: z.string(),
  avatar: z.string().optional(),
  baseStats: UnitStatsSchema,
  startOfCombat: z.array(AbilitySchema).optional(),
  onTrigger: z.array(AbilitySchema).optional(),
  positionalBonus: PositionalBonusSchema.optional(),
});
export type UnitDef = z.infer<typeof UnitDefSchema>;

export const UnitInstanceSchema = z.object({
  instanceId: z.string(),
  unitId: z.string(),
  starLevel: z.number().int().min(1).max(3).default(1),
});
export type UnitInstance = z.infer<typeof UnitInstanceSchema>;
