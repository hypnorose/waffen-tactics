import { describe, expect, it } from 'vitest';
import { buildApp } from '../src/app.js';

describe('server', () => {
  it('responds ok on /health', async () => {
    const app = buildApp();
    const res = await app.inject({ method: 'GET', url: '/health' });
    expect(res.statusCode).toBe(200);
    expect(res.json()).toEqual({ status: 'ok' });
  });

  it('serves the ported unit roster over /api/content/units', async () => {
    const app = buildApp();
    const res = await app.inject({ method: 'GET', url: '/api/content/units' });
    expect(res.statusCode).toBe(200);
    expect(res.json()).toHaveLength(32);
  });
});
