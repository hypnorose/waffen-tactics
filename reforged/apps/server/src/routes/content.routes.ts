import type { FastifyInstance } from 'fastify';
import { augmentDefs, botLadder, getTagDefs, getUnitList } from '@reforged/content-data';

export function registerContentRoutes(app: FastifyInstance): void {
  app.get('/api/content/units', async () => getUnitList());
  app.get('/api/content/tags', async () => getTagDefs());
  app.get('/api/content/augments', async () => augmentDefs);
  app.get('/api/content/bot-ladder', async () => botLadder);
}
