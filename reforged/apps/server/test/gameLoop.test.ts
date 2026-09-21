import { beforeEach, describe, expect, it } from 'vitest';
import type { FastifyInstance } from 'fastify';
import type { RunState } from '@reforged/schema';
import { buildApp } from '../src/app.js';
import { createDb, type Db } from '../src/db/client.js';
import { advanceRound, persistRun } from '../src/services/runService.js';
import { loginTestUser } from './testAuth.js';

let app: FastifyInstance;
let db: Db;
let token: string;

async function createRun() {
  const res = await app.inject({
    method: 'POST',
    url: '/api/run',
    headers: { authorization: `Bearer ${token}` },
  });
  return res.json() as RunState;
}

beforeEach(async () => {
  db = createDb(':memory:');
  app = buildApp(db);
  token = await loginTestUser(app, db, `discord-${Math.random()}`);
});

describe('full round loop: shop -> board -> reroll -> level -> augment', () => {
  it('walks a run through the whole economy + augment cycle', async () => {
    const run = await createRun();
    expect(run.status).toBe('active');
    expect(run.gold).toBe(50);

    // buy the first shop offer onto the bench
    const buyRes = await app.inject({
      method: 'POST',
      url: `/api/run/${run.runId}/buy`,
      headers: { authorization: `Bearer ${token}` },
      payload: { offerIndex: 0 },
    });
    expect(buyRes.statusCode).toBe(200);
    const afterBuy = buyRes.json() as RunState;
    expect(afterBuy.units).toHaveLength(1);
    expect(afterBuy.gold).toBeLessThan(run.gold);
    const unitInstanceId = afterBuy.units[0].instanceId;

    // place it on the 3x3 board
    const placeRes = await app.inject({
      method: 'POST',
      url: `/api/run/${run.runId}/board/place`,
      headers: { authorization: `Bearer ${token}` },
      payload: { unitInstanceId, position: { row: 1, col: 1 } },
    });
    expect(placeRes.statusCode).toBe(200);
    const afterPlace = placeRes.json() as RunState;
    const centerSlot = afterPlace.board.find((s) => s.position.row === 1 && s.position.col === 1);
    expect(centerSlot?.unitInstanceId).toBe(unitInstanceId);

    // reroll the shop
    const rerollRes = await app.inject({
      method: 'POST',
      url: `/api/run/${run.runId}/shop/reroll`,
      headers: { authorization: `Bearer ${token}` },
    });
    expect(rerollRes.statusCode).toBe(200);
    const afterReroll = rerollRes.json() as RunState;
    expect(afterReroll.gold).toBe(afterPlace.gold - 2);

    // buy xp until level 2 (costs 4 gold each, level 1 needs 4 xp)
    const buyXpRes = await app.inject({
      method: 'POST',
      url: `/api/run/${run.runId}/buy-xp`,
      headers: { authorization: `Bearer ${token}` },
    });
    expect(buyXpRes.statusCode).toBe(200);
    const afterXp = buyXpRes.json() as RunState;
    expect(afterXp.level).toBe(2);
    expect(afterXp.gold).toBe(afterReroll.gold - 4);

    // advance to round 2, which is an augment round
    const advanced = advanceRound(afterXp);
    expect(advanced.augmentPending).toBe(true);
    persistRun(db, advanced);

    const offersRes = await app.inject({
      method: 'GET',
      url: `/api/run/${run.runId}/augment/offers`,
      headers: { authorization: `Bearer ${token}` },
    });
    expect(offersRes.statusCode).toBe(200);
    const offers = offersRes.json() as Array<{ id: string; tier: string }>;
    expect(offers).toHaveLength(3);
    expect(offers.every((o) => o.tier === 'bronze')).toBe(true);

    const pickRes = await app.inject({
      method: 'POST',
      url: `/api/run/${run.runId}/augment/pick`,
      headers: { authorization: `Bearer ${token}` },
      payload: { augmentId: offers[0].id },
    });
    expect(pickRes.statusCode).toBe(200);
    const afterPick = pickRes.json() as RunState;
    expect(afterPick.augmentPending).toBe(false);
    expect(afterPick.augmentsPicked).toEqual([offers[0].id]);
  });

  it('rejects unauthenticated requests', async () => {
    const res = await app.inject({ method: 'POST', url: '/api/run' });
    expect(res.statusCode).toBe(401);
  });

  it('rejects acting on another user\'s run', async () => {
    const run = await createRun();
    const otherToken = await loginTestUser(app, db, `discord-other-${Math.random()}`);
    const res = await app.inject({
      method: 'GET',
      url: `/api/run/${run.runId}/state`,
      headers: { authorization: `Bearer ${otherToken}` },
    });
    expect(res.statusCode).toBe(403);
  });
});
