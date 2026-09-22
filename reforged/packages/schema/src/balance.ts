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

// Only 5 player levels — no XP, leveling is a direct gold purchase (see
// LEVEL_UP_BASE_COST below). Shop rarity odds by level — index 0..4 = cost
// tier 1..5, values are percentage weights (don't need to sum to 100, only
// relative weight matters).
export const MAX_LEVEL = 5;
export const SHOP_ODDS_BY_LEVEL: Record<number, [number, number, number, number, number]> = {
  1: [100, 0, 0, 0, 0],
  2: [55, 35, 10, 0, 0],
  3: [30, 35, 25, 10, 0],
  4: [15, 25, 30, 20, 10],
  5: [10, 15, 25, 30, 20],
};

export function shopOddsForLevel(level: number): [number, number, number, number, number] {
  return SHOP_ODDS_BY_LEVEL[Math.min(Math.max(level, 1), MAX_LEVEL)] ?? SHOP_ODDS_BY_LEVEL[1];
}

// Gold cost to buy the next level, keyed by current level (1->2, 2->3, ...).
// Gets cheaper every round (DECAY per round), floored at MIN so it never
// goes to zero — catching up late is always possible, just not free.
const LEVEL_UP_BASE_COST: Record<number, number> = { 1: 20, 2: 30, 3: 45, 4: 60 };
const LEVEL_UP_COST_DECAY_PER_ROUND = 2;
const LEVEL_UP_MIN_COST = 5;

/** null once already at MAX_LEVEL — there's nothing left to buy. */
export function levelUpCost(currentLevel: number, roundNumber: number): number | null {
  if (currentLevel >= MAX_LEVEL) return null;
  const base = LEVEL_UP_BASE_COST[currentLevel] ?? 0;
  return Math.max(LEVEL_UP_MIN_COST, base - (roundNumber - 1) * LEVEL_UP_COST_DECAY_PER_ROUND);
}
