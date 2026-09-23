import type { FastifyInstance } from 'fastify';
import { desc } from 'drizzle-orm';
import { getRankInfo } from '@reforged/schema';
import { discordAvatarUrl } from '../auth/discord.js';
import type { Db } from '../db/client.js';
import { users } from '../db/schema.js';

export function registerLeaderboardRoutes(app: FastifyInstance, db: Db): void {
  app.get('/api/leaderboard', async () => {
    const rows = db
      .select({ id: users.id, username: users.username, avatarHash: users.avatarHash, elo: users.elo })
      .from(users)
      .orderBy(desc(users.elo))
      .limit(20)
      .all();
    return rows.map((row) => ({
      username: row.username,
      avatarUrl: discordAvatarUrl({ id: row.id, avatarHash: row.avatarHash }),
      rank: getRankInfo(row.elo),
    }));
  });
}
