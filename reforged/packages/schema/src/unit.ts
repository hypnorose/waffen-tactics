import { z } from 'zod';
import { AbilitySchema } from './ability.js';
import { PositionalBonusSchema } from './positionalBonus.js';

// Stats exist only for deterministic simulation — never rendered as raw
// numbers in the UI (well, they are now shown — see UnitStatRow — but the
// point still stands that combat reads these, not a display layer). No
// defense stat: damage is never mitigated. Attack/attacksPerSecond are both
// optional — a unit with neither never attacks at all, and only acts
// through its startOfCombat/onTrigger abilities (e.g. a pure support unit
// that only shields or buffs allies).
export const UnitStatsSchema = z.object({
  attack: z.number().positive().optional(),
  attacksPerSecond: z.number().positive().optional(),
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
