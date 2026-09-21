import type { RunStatus } from '@reforged/schema';

// Elo only changes once a run actually concludes (10 wins or 5 losses), not
// after every match — placeholder balance, like the rest of the economy
// tables. Finishing the gauntlet is worth a flat bonus; busting out early is
// worth less the fewer wins were banked first.
const RUN_WIN_BONUS = 150;
const ELO_PER_WIN_ON_LOSS = 15;
const RUN_LOSS_BASE_PENALTY = 75;

/** Only call this when `status` is 'won' or 'lost' (i.e. the run just ended) — never for 'active'. */
export function runEloDelta(status: Exclude<RunStatus, 'active'>, wins: number): number {
  if (status === 'won') return RUN_WIN_BONUS;
  return wins * ELO_PER_WIN_ON_LOSS - RUN_LOSS_BASE_PENALTY;
}
