import type { AugmentDef, BoardPosition, CombatLog, RunState, Side, Tag, UnitDef, UserProfile } from '@reforged/schema';

// Relative by default: works unmodified once deployed same-origin behind
// Caddy. Dev proxies /api through Vite (see vite.config.ts) instead of
// needing an absolute VITE_API_BASE override.
const API_BASE = import.meta.env.VITE_API_BASE ?? '';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

let token: string | null = null;
export function setToken(next: string | null): void {
  token = next;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new ApiError(res.status, payload.error ?? res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  exchangeDiscordCode: (code: string) => request<{ token: string; profile: UserProfile }>('POST', '/api/auth/discord/exchange', { code }),
  getMe: () => request<UserProfile>('GET', '/api/me'),

  getUnits: () => request<UnitDef[]>('GET', '/api/content/units'),
  getTags: () => request<Tag[]>('GET', '/api/content/tags'),

  getCurrentRun: () => request<RunState>('GET', '/api/run/current'),
  createRun: () => request<RunState>('POST', '/api/run'),
  getRunState: (runId: string) => request<RunState>('GET', `/api/run/${runId}/state`),
  surrender: (runId: string) => request<RunState>('POST', `/api/run/${runId}/surrender`),

  reroll: (runId: string) => request<RunState>('POST', `/api/run/${runId}/shop/reroll`),
  toggleLock: (runId: string) => request<RunState>('POST', `/api/run/${runId}/shop/toggle-lock`),
  buy: (runId: string, offerIndex: number) => request<RunState>('POST', `/api/run/${runId}/buy`, { offerIndex }),
  sell: (runId: string, unitInstanceId: string) => request<RunState>('POST', `/api/run/${runId}/sell`, { unitInstanceId }),
  buyLevel: (runId: string) => request<RunState>('POST', `/api/run/${runId}/buy-level`),

  place: (runId: string, unitInstanceId: string, position: BoardPosition) =>
    request<RunState>('POST', `/api/run/${runId}/board/place`, { unitInstanceId, position }),
  bench: (runId: string, unitInstanceId: string) => request<RunState>('POST', `/api/run/${runId}/board/bench`, { unitInstanceId }),

  getAugmentOffers: (runId: string) => request<AugmentDef[]>('GET', `/api/run/${runId}/augment/offers`),
  pickAugment: (runId: string, augmentId: string) => request<RunState>('POST', `/api/run/${runId}/augment/pick`, { augmentId }),

  startCombat: (runId: string) =>
    request<{ run: RunState; combatLog: CombatLog; winner: Side; opponentName: string; opponentAvatarUrl: string | null }>(
      'POST',
      `/api/run/${runId}/combat/start`,
    ),
};
