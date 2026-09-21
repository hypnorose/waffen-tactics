import type { FastifyInstance } from 'fastify';
import { getRankInfo } from '@reforged/schema';
import { requireAuth } from '../auth/middleware.js';
import { discordAvatarUrl } from '../auth/discord.js';
import type { Db } from '../db/client.js';
import { findUserById } from '../db/userRepository.js';

export function registerProfileRoutes(app: FastifyInstance, db: Db): void {
  app.get('/api/me', { preHandler: requireAuth }, async (request, reply) => {
    const user = findUserById(db, request.user.userId);
    if (!user) return reply.code(404).send({ error: 'user_not_found' });

    return reply.send({
      discordId: user.id,
      username: user.username,
      avatarUrl: discordAvatarUrl({ id: user.id, avatarHash: user.avatarHash }),
      rank: getRankInfo(user.elo),
    });
  });
}
