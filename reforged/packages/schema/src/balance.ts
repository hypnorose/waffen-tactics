/**
 * Shared placeholder balance: how much of a team's shared HP pool a unit
 * contributes, derived from cost. Lives here (not just in the combat
 * orchestrator) so the UI can show the same number it actually fights with —
 * single source of truth, no drift between what's displayed and what's real.
 */
export const BASE_UNIT_HP = 50;
export const HP_PER_COST = 20;

export function unitHpContribution(cost: number): number {
  return BASE_UNIT_HP + cost * HP_PER_COST;
}
