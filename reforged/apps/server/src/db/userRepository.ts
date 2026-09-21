import { randomUUID } from 'node:crypto';
import { eq } from 'drizzle-orm';
import type { Db } from './client.js';
import { users } from './schema.js';

export interface User {
  id: string;
  email: string;
  passwordHash: string;
}

export function findUserByEmail(db: Db, email: string): User | null {
  const row = db.select().from(users).where(eq(users.email, email)).get();
  return row ?? null;
}

export function createUser(db: Db, email: string, passwordHash: string): User {
  const id = randomUUID();
  db.insert(users).values({ id, email, passwordHash, createdAt: Date.now() }).run();
  return { id, email, passwordHash };
}
