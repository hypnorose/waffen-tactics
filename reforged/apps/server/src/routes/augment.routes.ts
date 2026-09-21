import type { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { augmentDefs } from '@reforged/content-data';
import type { Db } from '../db/client.js';
import { requireAuth } from '../auth/middleware.js';
import { persistRun, requireOwnedRun } from '../services/runService.js';
import * as augmentService from '../services/augmentService.js';
import { handleServiceError } from './errors.js';

const PickSchema = z.object({ augmentId: z.string() });

export function registerAugmentRoutes(app: FastifyInstance, db: Db): void {
  app.get<{ Params: { id: string } }>(
    '/api/run/:id/augment/offers',
    { preHandler: requireAuth },
    async (request, reply) => {
      try {
        const run = requireOwnedRun(db, request.user.userId, request.params.id);
        const updated = persistRun(db, augmentService.ensureOffers(run));
        const offers = augmentDefs.filter((a) => updated.augmentOffers?.includes(a.id));
        return reply.send(offers);
      } catch (err) {
        return handleServiceError(reply, err);
      }
    },
  );

  app.post<{ Params: { id: string } }>(
    '/api/run/:id/augment/pick',
    { preHandler: requireAuth },
    async (request, reply) => {
      const parsed = PickSchema.safeParse(request.body);
      if (!parsed.success) return reply.code(400).send({ error: 'invalid_body' });
      try {
        const run = requireOwnedRun(db, request.user.userId, request.params.id);
        const updated = persistRun(db, augmentService.pick(run, parsed.data.augmentId));
        return reply.send(updated);
      } catch (err) {
        return handleServiceError(reply, err);
      }
    },
  );
}
