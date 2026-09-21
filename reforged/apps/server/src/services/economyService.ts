import type { UnitDef } from '@reforged/schema';

/**
 * Shop rarity odds and the xp curve below are placeholder MVP balance — real
 * tuning is a content/balance pass (plan Phase 4 follow-up), not an infra
 * decision. Kept here as pure, easily-swappable tables.
 */
const SHOP_ODDS_BY_LEVEL: Record<number, [number, number, number, number, number]> = {
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

export const MAX_LEVEL = 10;
export const STARTING_GOLD = 10;
export const REROLL_COST = 2;
export const BUY_XP_COST = 4;
export const BUY_XP_AMOUNT = 4;
export const MAX_BENCH_SIZE = 9;

/** Board capacity is fixed at the full 3x3 grid from round 1 — it does not scale with level. */
export function maxBoardUnits(_level: number): number {
  return 9;
}

export function xpToNextLevel(level: number): number | null {
  return XP_TO_NEXT_LEVEL[level] ?? null;
}

/** Applies gained xp, cascading through as many level-ups as it earns. */
export function applyXp(level: number, xp: number, xpGained: number): { level: number; xp: number } {
  let nextLevel = level;
  let nextXp = xp + xpGained;

  for (;;) {
    const required = xpToNextLevel(nextLevel);
    if (required === null || nextXp < required) break;
    nextXp -= required;
    nextLevel += 1;
  }

  return { level: nextLevel, xp: nextXp };
}

/** Flat base income + savings interest (1 gold per 10 gold saved, capped at 5). */
export function roundIncome(gold: number): number {
  const interest = Math.min(5, Math.floor(gold / 10));
  return 5 + interest;
}

function pickWeighted<T>(items: T[], weights: number[]): T {
  const total = weights.reduce((sum, w) => sum + w, 0);
  let roll = Math.random() * total;
  for (let i = 0; i < items.length; i++) {
    roll -= weights[i];
    if (roll <= 0) return items[i];
  }
  return items[items.length - 1];
}

export function rollShopOffers(level: number, unitPool: UnitDef[]): Array<string | null> {
  const odds = SHOP_ODDS_BY_LEVEL[Math.min(level, MAX_LEVEL)] ?? SHOP_ODDS_BY_LEVEL[1];
  const byCost = new Map<number, UnitDef[]>();
  for (const unit of unitPool) {
    const bucket = byCost.get(unit.cost) ?? [];
    bucket.push(unit);
    byCost.set(unit.cost, bucket);
  }

  const costTiers = [1, 2, 3, 4, 5].filter((cost) => (byCost.get(cost)?.length ?? 0) > 0);
  const weights = costTiers.map((cost) => odds[cost - 1]);

  return Array.from({ length: 5 }, () => {
    const cost = pickWeighted(costTiers, weights);
    const pool = byCost.get(cost)!;
    return pool[Math.floor(Math.random() * pool.length)].id;
  });
}
