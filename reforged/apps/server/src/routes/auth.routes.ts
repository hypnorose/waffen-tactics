import type { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { getRankInfo } from '@reforged/schema';
import { discordAvatarUrl, exchangeDiscordCode, DiscordAuthError } from '../auth/discord.js';
import type { Db } from '../db/client.js';
import { upsertDiscordUser } from '../db/userRepository.js';

const ExchangeSchema = z.object({ code: z.string().min(1) });

export function registerAuthRoutes(app: FastifyInstance, db: Db): void {
  app.post('/api/auth/discord/exchange', async (request, reply) => {
    const parsed = ExchangeSchema.safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'missing_code' });

    try {
      const discordUser = await exchangeDiscordCode(parsed.data.code);
      const user = upsertDiscordUser(db, discordUser);
      const token = app.jwt.sign({ userId: user.id });

      return reply.send({
        token,
        profile: {
          discordId: user.id,
          username: user.username,
          avatarUrl: discordAvatarUrl({ id: user.id, avatarHash: user.avatarHash }),
          rank: getRankInfo(user.elo),
        },
      });
    } catch (err) {
      if (err instanceof DiscordAuthError) return reply.code(401).send({ error: err.message });
      throw err;
    }
  });
}
