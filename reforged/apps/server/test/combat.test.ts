import { beforeEach, describe, expect, it } from 'vitest';
import type { FastifyInstance } from 'fastify';
import type { RunState } from '@reforged/schema';
import { buildApp } from '../src/app.js';
import { createDb, type Db } from '../src/db/client.js';
import { loginTestUser } from './testAuth.js';

let app: FastifyInstance;
let db: Db;
let token: string;

beforeEach(async () => {
  db = createDb(':memory:');
  app = buildApp(db);
  token = await loginTestUser(app, db, `discord-fighter-${Math.random()}`);
});

async function createRunWithBoardedUnit(authToken = token) {
  const runRes = await app.inject({ method: 'POST', url: '/api/run', headers: { authorization: `Bearer ${authToken}` } });
  const run = runRes.json() as RunState;

  const buyRes = await app.inject({
    method: 'POST',
    url: `/api/run/${run.runId}/buy`,
    headers: { authorization: `Bearer ${authToken}` },
    payload: { offerIndex: 0 },
  });
  const afterBuy = buyRes.json() as RunState;
  const unitInstanceId = afterBuy.units[0].instanceId;

  await app.inject({
    method: 'POST',
    url: `/api/run/${run.runId}/board/place`,
    headers: { authorization: `Bearer ${authToken}` },
    payload: { unitInstanceId, position: { row: 1, col: 1 } },
  });

  return run.runId;
}

describe('combat orchestration', () => {
  it('refuses to fight with an empty board', async () => {
    const runRes = await app.inject({ method: 'POST', url: '/api/run', headers: { authorization: `Bearer ${token}` } });
    const run = runRes.json() as RunState;

    const res = await app.inject({
      method: 'POST',
      url: `/api/run/${run.runId}/combat/start`,
      headers: { authorization: `Bearer ${token}` },
    });
    expect(res.statusCode).toBe(400);
  });

  it('runs a fight against the PvE bot ladder and applies the result', async () => {
    const runId = await createRunWithBoardedUnit();

    const res = await app.inject({
      method: 'POST',
      url: `/api/run/${runId}/combat/start`,
      headers: { authorization: `Bearer ${token}` },
    });
    expect(res.statusCode).toBe(200);
    const body = res.json() as { run: RunState; combatLog: { combatId: string; events: unknown[] }; winner: string };

    expect(['player', 'enemy']).toContain(body.winner);
    expect(body.combatLog.events.length).toBeGreaterThan(0);
    expect(body.run.wins + body.run.losses).toBe(1);
    // a fight always counts as a round played
    expect(body.run.roundNumber === 2 || body.run.status !== 'active').toBe(true);

    // the persisted log is independently fetchable by its owner
    const fetchRes = await app.inject({
      method: 'GET',
      url: `/api/combat/${body.combatLog.combatId}`,
      headers: { authorization: `Bearer ${token}` },
    });
    expect(fetchRes.statusCode).toBe(200);
    expect(fetchRes.json().combatId).toBe(body.combatLog.combatId);
  });

  it('prefers a snapshot of another real player at the same round over the bot ladder', async () => {
    // Seed a snapshot: user A fights once at round 1.
    const opponentId = `discord-fighter-${Math.random()}`;
    const opponentToken = await loginTestUser(app, db, opponentId, 'avatar-hash');
    const runIdA = await createRunWithBoardedUnit(opponentToken);
    const startResA = await app.inject({
      method: 'POST',
      url: `/api/run/${runIdA}/combat/start`,
      headers: { authorization: `Bearer ${opponentToken}` },
    });
    expect(startResA.statusCode).toBe(200);

    // User B's very first fight (also round 1, same starting elo) should be
    // matched against A's snapshot instead of a bot.
    const otherToken = await loginTestUser(app, db, `discord-other-${Math.random()}`);
    const runRes = await app.inject({
      method: 'POST',
      url: '/api/run',
      headers: { authorization: `Bearer ${otherToken}` },
    });
    const run = runRes.json() as RunState;
    const buyRes = await app.inject({
      method: 'POST',
      url: `/api/run/${run.runId}/buy`,
      headers: { authorization: `Bearer ${otherToken}` },
      payload: { offerIndex: 0 },
    });
    const unitInstanceId = (buyRes.json() as RunState).units[0].instanceId;
    await app.inject({
      method: 'POST',
      url: `/api/run/${run.runId}/board/place`,
      headers: { authorization: `Bearer ${otherToken}` },
      payload: { unitInstanceId, position: { row: 1, col: 1 } },
    });

    const res = await app.inject({
      method: 'POST',
      url: `/api/run/${run.runId}/combat/start`,
      headers: { authorization: `Bearer ${otherToken}` },
    });
    expect(res.statusCode).toBe(200);
    const body = res.json() as { opponentName: string; opponentAvatarUrl: string | null };
    expect(body.opponentName).toBe(`player-${opponentId}`);
    expect(body.opponentAvatarUrl).toBe(`https://cdn.discordapp.com/avatars/${opponentId}/avatar-hash.png?size=128`);
  });

  it('rejects fetching another user\'s combat log', async () => {
    const runId = await createRunWithBoardedUnit();
    const startRes = await app.inject({
      method: 'POST',
      url: `/api/run/${runId}/combat/start`,
      headers: { authorization: `Bearer ${token}` },
    });
    const { combatLog } = startRes.json();

    const otherToken = await loginTestUser(app, db, `discord-other-${Math.random()}`);
    const res = await app.inject({
      method: 'GET',
      url: `/api/combat/${combatLog.combatId}`,
      headers: { authorization: `Bearer ${otherToken}` },
    });
    expect(res.statusCode).toBe(403);
  });
});
