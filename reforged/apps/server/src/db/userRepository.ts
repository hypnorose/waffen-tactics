import { eq } from 'drizzle-orm';
import { STARTING_ELO } from '@reforged/schema';
import type { Db } from './client.js';
import { users } from './schema.js';

export interface User {
  id: string;
  username: string;
  avatarHash: string | null;
  elo: number;
}

export function findUserById(db: Db, id: string): User | null {
  const row = db.select().from(users).where(eq(users.id, id)).get();
  return row ?? null;
}

/** Upserts by Discord id — first login creates the row, later logins refresh username/avatar. */
export function upsertDiscordUser(db: Db, discordUser: { id: string; username: string; avatarHash: string | null }): User {
  const existing = findUserById(db, discordUser.id);
  if (existing) {
    db.update(users)
      .set({ username: discordUser.username, avatarHash: discordUser.avatarHash })
      .where(eq(users.id, discordUser.id))
      .run();
    return { ...existing, username: discordUser.username, avatarHash: discordUser.avatarHash };
  }

  const user: User = { id: discordUser.id, username: discordUser.username, avatarHash: discordUser.avatarHash, elo: STARTING_ELO };
  db.insert(users)
    .values({ ...user, createdAt: Date.now() })
    .run();
  return user;
}

export function updateElo(db: Db, userId: string, elo: number): void {
  db.update(users).set({ elo }).where(eq(users.id, userId)).run();
}
