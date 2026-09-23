import { describe, expect, it } from 'vitest';
import { buildApp } from '../src/app.js';
import { createDb } from '../src/db/client.js';
import { updateElo } from '../src/db/userRepository.js';
import { loginTestUser } from './testAuth.js';

describe('leaderboard', () => {
  it('returns players ordered by elo with avatars and divisions', async () => {
    const db = createDb(':memory:');
    const app = buildApp(db);
    await loginTestUser(app, db, 'discord-low', null);
    await loginTestUser(app, db, 'discord-high', 'high-avatar');
    updateElo(db, 'discord-high', 1800);

    const res = await app.inject({ method: 'GET', url: '/api/leaderboard' });

    expect(res.statusCode).toBe(200);
    expect(res.json()).toEqual([
      {
        username: 'player-discord-high',
        avatarUrl: 'https://cdn.discordapp.com/avatars/discord-high/high-avatar.png?size=128',
        rank: { tier: 'diamond', division: 4, elo: 1800 },
      },
      {
        username: 'player-discord-low',
        avatarUrl: null,
        rank: { tier: 'bronze', division: 1, elo: 1000 },
      },
    ]);
  });
});
