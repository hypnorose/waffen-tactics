import type { FastifyInstance } from 'fastify';
import { z } from 'zod';
import type { Db } from '../db/client.js';
import { requireAuth } from '../auth/middleware.js';
import { persistRun, requireOwnedRun } from '../services/runService.js';
import * as shopService from '../services/shopService.js';
import { InsufficientGoldError } from '../services/shopService.js';
import { levelUpCost } from '../services/economyService.js';
import { handleServiceError } from './errors.js';

const BuySchema = z.object({ offerIndex: z.number().int().min(0).max(4) });
const SellSchema = z.object({ unitInstanceId: z.string() });

export function registerShopRoutes(app: FastifyInstance, db: Db): void {
  app.post<{ Params: { id: string } }>(
    '/api/run/:id/shop/reroll',
    { preHandler: requireAuth },
    async (request, reply) => {
      try {
        const run = requireOwnedRun(db, request.user.userId, request.params.id);
        const updated = persistRun(db, shopService.reroll(run));
        return reply.send(updated);
      } catch (err) {
        return handleServiceError(reply, err);
      }
    },
  );

  app.post<{ Params: { id: string } }>(
    '/api/run/:id/shop/toggle-lock',
    { preHandler: requireAuth },
    async (request, reply) => {
      try {
        const run = requireOwnedRun(db, request.user.userId, request.params.id);
        const updated = persistRun(db, shopService.toggleLock(run));
        return reply.send(updated);
      } catch (err) {
        return handleServiceError(reply, err);
      }
    },
  );

  app.post<{ Params: { id: string } }>('/api/run/:id/buy', { preHandler: requireAuth }, async (request, reply) => {
    const parsed = BuySchema.safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'invalid_body' });
    try {
      const run = requireOwnedRun(db, request.user.userId, request.params.id);
      const updated = persistRun(db, shopService.buy(run, parsed.data.offerIndex));
      return reply.send(updated);
    } catch (err) {
      return handleServiceError(reply, err);
    }
  });

  app.post<{ Params: { id: string } }>('/api/run/:id/sell', { preHandler: requireAuth }, async (request, reply) => {
    const parsed = SellSchema.safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'invalid_body' });
    try {
      const run = requireOwnedRun(db, request.user.userId, request.params.id);
      const updated = persistRun(db, shopService.sell(run, parsed.data.unitInstanceId));
      return reply.send(updated);
    } catch (err) {
      return handleServiceError(reply, err);
    }
  });

  app.post<{ Params: { id: string } }>('/api/run/:id/buy-level', { preHandler: requireAuth }, async (request, reply) => {
    try {
      const run = requireOwnedRun(db, request.user.userId, request.params.id);
      const cost = levelUpCost(run.level, run.roundNumber);
      if (cost === null) throw new InsufficientGoldError();
      if (run.gold < cost) throw new InsufficientGoldError();
      const updated = persistRun(db, { ...run, gold: run.gold - cost, level: run.level + 1 });
      return reply.send(updated);
    } catch (err) {
      return handleServiceError(reply, err);
    }
  });
}
