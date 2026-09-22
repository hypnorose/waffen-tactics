import type { FastifyInstance } from 'fastify';
import type { Db } from '../src/db/client.js';
import { upsertDiscordUser } from '../src/db/userRepository.js';

/** Bypasses the real Discord round-trip for tests — upserts a user directly and signs the same JWT the exchange route would. */
export async function loginTestUser(app: FastifyInstance, db: Db, discordId: string, avatarHash: string | null = null): Promise<string> {
  await app.ready();
  const user = upsertDiscordUser(db, { id: discordId, username: `player-${discordId}`, avatarHash });
  return app.jwt.sign({ userId: user.id });
}
