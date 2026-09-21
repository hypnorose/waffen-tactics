import type { FastifyInstance } from 'fastify';
import type { Db } from '../src/db/client.js';
import { upsertDiscordUser } from '../src/db/userRepository.js';

/** Bypasses the real Discord round-trip for tests — upserts a user directly and signs the same JWT the exchange route would. */
export async function loginTestUser(app: FastifyInstance, db: Db, discordId: string): Promise<string> {
  await app.ready();
  const user = upsertDiscordUser(db, { id: discordId, username: `player-${discordId}`, avatarHash: null });
  return app.jwt.sign({ userId: user.id });
}
