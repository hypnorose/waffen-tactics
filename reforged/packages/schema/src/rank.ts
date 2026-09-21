import { z } from 'zod';

export const RankTierSchema = z.enum(['bronze', 'silver', 'gold', 'platinum', 'diamond', 'master']);
export type RankTier = z.infer<typeof RankTierSchema>;

export const RankInfoSchema = z.object({
  tier: RankTierSchema,
  division: z.number().int().min(1).max(4).nullable(),
  elo: z.number().int(),
});
export type RankInfo = z.infer<typeof RankInfoSchema>;

const TIER_FLOORS: Array<{ tier: RankTier; floor: number }> = [
  { tier: 'bronze', floor: 0 },
  { tier: 'silver', floor: 1200 },
  { tier: 'gold', floor: 1400 },
  { tier: 'platinum', floor: 1600 },
  { tier: 'diamond', floor: 1800 },
  { tier: 'master', floor: 2000 },
];

// Every tier below Master spans 200 elo, split into 4 divisions (IV lowest
// -> I highest) of 50 elo each. Master has no divisions, just a raw elo
// leaderboard — the classic Bronze..Diamond-with-divisions / Master-as-pure-
// -MMR shape the user asked for.
const DIVISION_SPAN = 50;

export function getRankInfo(elo: number): RankInfo {
  let current = TIER_FLOORS[0];
  for (const t of TIER_FLOORS) {
    if (elo >= t.floor) current = t;
  }

  if (current.tier === 'master') {
    return { tier: 'master', division: null, elo };
  }

  const withinTier = elo - current.floor;
  const divisionIndex = Math.min(3, Math.max(0, Math.floor(withinTier / DIVISION_SPAN)));
  const division = 4 - divisionIndex;
  return { tier: current.tier, division, elo };
}

export const STARTING_ELO = 1000;
