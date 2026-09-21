import cors from '@fastify/cors';
import jwt from '@fastify/jwt';
import Fastify from 'fastify';
import './auth/jwt.js';
import { createDb, type Db } from './db/client.js';
import { config } from './config.js';
import { registerAuthRoutes } from './routes/auth.routes.js';
import { registerRunRoutes } from './routes/run.routes.js';
import { registerShopRoutes } from './routes/shop.routes.js';
import { registerBoardRoutes } from './routes/board.routes.js';
import { registerAugmentRoutes } from './routes/augment.routes.js';
import { registerCombatRoutes } from './routes/combat.routes.js';
import { registerContentRoutes } from './routes/content.routes.js';
import { registerLeaderboardRoutes } from './routes/leaderboard.routes.js';

export function buildApp(db: Db = createDb(config.dbFile)) {
  const app = Fastify({ logger: true });

  app.register(cors, { origin: true });
  app.register(jwt, { secret: config.jwtSecret });

  app.get('/health', async () => ({ status: 'ok' }));

  registerAuthRoutes(app, db);
  registerRunRoutes(app, db);
  registerShopRoutes(app, db);
  registerBoardRoutes(app, db);
  registerAugmentRoutes(app, db);
  registerCombatRoutes(app, db);
  registerContentRoutes(app);
  registerLeaderboardRoutes(app, db);

  return app;
}
