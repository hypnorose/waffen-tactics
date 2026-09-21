import { findClosestBot, type BotProfile } from '@reforged/content-data';
import type { RunState } from '@reforged/schema';

/** PvE-only in MVP (plan decision #8) — picks the bot ladder entry closest to the run's current wins. */
export function findOpponent(run: RunState): BotProfile {
  return findClosestBot(run.wins);
}
