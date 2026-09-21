import type { FastifyInstance } from 'fastify';
import type { Db } from '../db/client.js';
import { getCombatLogById, getCombatLogRunId } from '../db/combatLogRepository.js';
import { requireAuth } from '../auth/middleware.js';
import { requireOwnedRun } from '../services/runService.js';
import { runCombatForRun } from '../services/combatOrchestrator.js';
import { handleServiceError } from './errors.js';

export function registerCombatRoutes(app: FastifyInstance, db: Db): void {
  app.post<{ Params: { id: string } }>(
    '/api/run/:id/combat/start',
    { preHandler: requireAuth },
    async (request, reply) => {
      try {
        const run = requireOwnedRun(db, request.user.userId, request.params.id);
        const result = runCombatForRun(db, run);
        return reply.send(result);
      } catch (err) {
        return handleServiceError(reply, err);
      }
    },
  );

  app.get<{ Params: { id: string } }>('/api/combat/:id', { preHandler: requireAuth }, async (request, reply) => {
    const log = getCombatLogById(db, request.params.id);
    const runId = getCombatLogRunId(db, request.params.id);
    if (!log || !runId) return reply.code(404).send({ error: 'combat_not_found' });

    try {
      requireOwnedRun(db, request.user.userId, runId);
    } catch (err) {
      return handleServiceError(reply, err);
    }

    return reply.send(log);
  });
}
