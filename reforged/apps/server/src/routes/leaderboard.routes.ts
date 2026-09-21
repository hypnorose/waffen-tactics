import type { FastifyInstance } from 'fastify';
import { desc, eq } from 'drizzle-orm';
import type { Db } from '../db/client.js';
import { runs, users } from '../db/schema.js';

export function registerLeaderboardRoutes(app: FastifyInstance, db: Db): void {
  app.get('/api/leaderboard', async () => {
    return db
      .select({ email: users.email, wins: runs.wins, losses: runs.losses, status: runs.status })
      .from(runs)
      .innerJoin(users, eq(runs.userId, users.id))
      .orderBy(desc(runs.wins))
      .limit(20)
      .all();
  });
}
