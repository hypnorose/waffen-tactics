import type { BotProfile } from '@reforged/content-data';

const BASE_ELO_GAIN = 15;
const ELO_GAIN_PER_BOT_LEVEL = 3;
const ELO_LOSS = 15;

/** Beating a harder bot on the ladder is worth more elo; losing always costs the same flat amount. */
export function eloDelta(won: boolean, opponent: BotProfile): number {
  if (!won) return -ELO_LOSS;
  return BASE_ELO_GAIN + opponent.level * ELO_GAIN_PER_BOT_LEVEL;
}
