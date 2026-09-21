/**
 * Shared placeholder balance tables — kept here (not just server-side) so
 * the UI can show the exact same numbers the server computes with (no drift
 * between what's displayed and what's real). Real tuning is a future
 * content/balance pass, not an infra decision.
 */

// How much of a team's shared HP pool a unit contributes, derived from cost.
export const BASE_UNIT_HP = 50;
export const HP_PER_COST = 20;

export function unitHpContribution(cost: number): number {
  return BASE_UNIT_HP + cost * HP_PER_COST;
}

// Shop rarity odds by player level — index 0..4 = cost tier 1..5, values are
// percentage weights (don't need to sum to 100, only relative weight matters).
export const MAX_LEVEL = 10;
export const SHOP_ODDS_BY_LEVEL: Record<number, [number, number, number, number, number]> = {
  1: [100, 0, 0, 0, 0],
  2: [75, 25, 0, 0, 0],
  3: [55, 30, 15, 0, 0],
  4: [45, 33, 20, 2, 0],
  5: [35, 32, 25, 8, 0],
  6: [25, 30, 30, 13, 2],
  7: [19, 25, 30, 20, 6],
  8: [15, 20, 30, 25, 10],
  9: [10, 15, 25, 30, 20],
  10: [5, 10, 20, 30, 35],
};

export function shopOddsForLevel(level: number): [number, number, number, number, number] {
  return SHOP_ODDS_BY_LEVEL[Math.min(Math.max(level, 1), MAX_LEVEL)] ?? SHOP_ODDS_BY_LEVEL[1];
}

// XP required to advance FROM this level to the next one; undefined at MAX_LEVEL (no further level-ups).
const XP_TO_NEXT_LEVEL: Record<number, number> = {
  1: 4,
  2: 8,
  3: 14,
  4: 22,
  5: 32,
  6: 48,
  7: 68,
  8: 92,
  9: 120,
};

export function xpToNextLevel(level: number): number | null {
  return XP_TO_NEXT_LEVEL[level] ?? null;
}
