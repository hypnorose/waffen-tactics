import type { FastifyInstance } from 'fastify';
import type { Db } from '../db/client.js';
import { requireAuth } from '../auth/middleware.js';
import { createRun, getCurrentRun, persistRun, requireOwnedRun } from '../services/runService.js';
import { handleServiceError } from './errors.js';

export function registerRunRoutes(app: FastifyInstance, db: Db): void {
  app.post('/api/run', { preHandler: requireAuth }, async (request, reply) => {
    const run = createRun(db, request.user.userId);
    return reply.code(201).send(run);
  });

  app.get('/api/run/current', { preHandler: requireAuth }, async (request, reply) => {
    const run = getCurrentRun(db, request.user.userId);
    if (!run) return reply.code(404).send({ error: 'no_active_run' });
    return reply.send(run);
  });

  app.get<{ Params: { id: string } }>('/api/run/:id', { preHandler: requireAuth }, async (request, reply) => {
    try {
      const run = requireOwnedRun(db, request.user.userId, request.params.id);
      return reply.send(run);
    } catch (err) {
      return handleServiceError(reply, err);
    }
  });

  app.get<{ Params: { id: string } }>('/api/run/:id/state', { preHandler: requireAuth }, async (request, reply) => {
    try {
      const run = requireOwnedRun(db, request.user.userId, request.params.id);
      return reply.send(run);
    } catch (err) {
      return handleServiceError(reply, err);
    }
  });

  app.post<{ Params: { id: string } }>(
    '/api/run/:id/surrender',
    { preHandler: requireAuth },
    async (request, reply) => {
      try {
        const run = requireOwnedRun(db, request.user.userId, request.params.id);
        const updated = persistRun(db, { ...run, status: 'lost' });
        return reply.send(updated);
      } catch (err) {
        return handleServiceError(reply, err);
      }
    },
  );
}
