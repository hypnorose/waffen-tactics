import type { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { hashPassword, verifyPassword } from '../auth/password.js';
import type { Db } from '../db/client.js';
import { createUser, findUserByEmail } from '../db/userRepository.js';

const CredentialsSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

export function registerAuthRoutes(app: FastifyInstance, db: Db): void {
  app.post('/api/auth/register', async (request, reply) => {
    const parsed = CredentialsSchema.safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'invalid_credentials' });

    const { email, password } = parsed.data;
    if (findUserByEmail(db, email)) return reply.code(409).send({ error: 'email_taken' });

    const passwordHash = await hashPassword(password);
    const user = createUser(db, email, passwordHash);
    const token = app.jwt.sign({ userId: user.id });
    return reply.code(201).send({ token });
  });

  app.post('/api/auth/login', async (request, reply) => {
    const parsed = CredentialsSchema.safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'invalid_credentials' });

    const { email, password } = parsed.data;
    const user = findUserByEmail(db, email);
    if (!user || !(await verifyPassword(password, user.passwordHash))) {
      return reply.code(401).send({ error: 'invalid_credentials' });
    }

    const token = app.jwt.sign({ userId: user.id });
    return reply.send({ token });
  });
}
