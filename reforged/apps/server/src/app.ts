import cors from '@fastify/cors';
import Fastify from 'fastify';
import { augmentDefs, botLadder, getTagDefs, getUnitList } from '@reforged/content-data';

export function buildApp() {
  const app = Fastify({ logger: true });

  app.register(cors, { origin: true });

  app.get('/health', async () => ({ status: 'ok' }));

  app.get('/api/content/units', async () => getUnitList());
  app.get('/api/content/tags', async () => getTagDefs());
  app.get('/api/content/augments', async () => augmentDefs);
  app.get('/api/content/bot-ladder', async () => botLadder);

  return app;
}
