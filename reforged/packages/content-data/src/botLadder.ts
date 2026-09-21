import { z } from 'zod';

/**
 * PvE-only opponent ladder (no live PvP in MVP — see plan decision #8),
 * loosely modeled on the legacy encounter_definitions.py profiles: each bot
 * is authored with a wins/losses/level "as if this is where a real player
 * would be", used by matchmaking to pick an opponent close to the run's
 * current wins count.
 */
export const BotProfileSchema = z.object({
  id: z.string(),
  name: z.string(),
  wins: z.number().int().min(0),
  losses: z.number().int().min(0),
  level: z.number().int().min(1).max(10),
  unitIds: z.array(z.string()).min(1).max(9),
});
export type BotProfile = z.infer<typeof BotProfileSchema>;

const raw: BotProfile[] = [
  { id: 'tutorial-bot', name: 'Bot Treningowy', wins: 0, losses: 0, level: 1, unitIds: ['anamol04'] },
  { id: 'bronze-bot', name: 'Brazowy Rywal', wins: 1, losses: 1, level: 2, unitIds: ['anamol04', 'uhla'] },
  { id: 'silver-bot', name: 'Srebrny Rywal', wins: 3, losses: 2, level: 4, unitIds: ['fiko', 'yossarian', 'sofronow'] },
  {
    id: 'gold-bot',
    name: 'Zloty Rywal',
    wins: 5,
    losses: 3,
    level: 6,
    unitIds: ['chessowy_mentos', 'pytl', 'boczek', 'kaktusek'],
  },
  {
    id: 'platinum-bot',
    name: 'Platynowy Rywal',
    wins: 7,
    losses: 4,
    level: 8,
    unitIds: ['knauff', 'vitas', 'szachowymentor', 'merex', 'fallensmokk'],
  },
  {
    id: 'diamond-bot',
    name: 'Diamentowy Rywal',
    wins: 9,
    losses: 4,
    level: 10,
    unitIds: ['9wojtaz9', 'marcel_galadotka', 'klemens_zydoslawski', 'nicosc', 'jadlainwestycji', 'empty_melancholy'],
  },
];

export const botLadder: BotProfile[] = raw.map((bot) => BotProfileSchema.parse(bot));

export function findClosestBot(wins: number): BotProfile {
  return botLadder.reduce((closest, bot) =>
    Math.abs(bot.wins - wins) < Math.abs(closest.wins - wins) ? bot : closest,
  );
}
