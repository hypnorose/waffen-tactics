import type { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { BoardPositionSchema } from '@reforged/schema';
import type { Db } from '../db/client.js';
import { requireAuth } from '../auth/middleware.js';
import { persistRun, requireOwnedRun } from '../services/runService.js';
import * as boardService from '../services/boardService.js';
import { handleServiceError } from './errors.js';

const PlaceSchema = z.object({ unitInstanceId: z.string(), position: BoardPositionSchema });
const BenchSchema = z.object({ unitInstanceId: z.string() });

export function registerBoardRoutes(app: FastifyInstance, db: Db): void {
  app.post<{ Params: { id: string } }>(
    '/api/run/:id/board/place',
    { preHandler: requireAuth },
    async (request, reply) => {
      const parsed = PlaceSchema.safeParse(request.body);
      if (!parsed.success) return reply.code(400).send({ error: 'invalid_body' });
      try {
        const run = requireOwnedRun(db, request.user.userId, request.params.id);
        const updated = persistRun(db, boardService.place(run, parsed.data.unitInstanceId, parsed.data.position));
        return reply.send(updated);
      } catch (err) {
        return handleServiceError(reply, err);
      }
    },
  );

  app.post<{ Params: { id: string } }>(
    '/api/run/:id/board/bench',
    { preHandler: requireAuth },
    async (request, reply) => {
      const parsed = BenchSchema.safeParse(request.body);
      if (!parsed.success) return reply.code(400).send({ error: 'invalid_body' });
      try {
        const run = requireOwnedRun(db, request.user.userId, request.params.id);
        const updated = persistRun(db, boardService.bench(run, parsed.data.unitInstanceId));
        return reply.send(updated);
      } catch (err) {
        return handleServiceError(reply, err);
      }
    },
  );
}
