import { create } from 'zustand';
import type { AugmentDef, BoardPosition, CombatLog, RunState, Side, Tag, UnitDef } from '@reforged/schema';
import { api, ApiError } from '../services/api.js';
import { useAuthStore } from './authStore.js';

interface RunStoreState {
  run: RunState | null;
  units: Record<string, UnitDef>;
  tags: Record<string, Tag>;
  augments: Record<string, AugmentDef>;
  lastCombat: {
    combatLog: CombatLog;
    winner: Side;
    opponentName: string;
    opponentAvatarUrl: string | null;
    opponentAugmentsPicked: string[];
  } | null;
  loading: boolean;
  error: string | null;

  loadContent: () => Promise<void>;
  loadOrCreateRun: () => Promise<void>;
  buy: (offerIndex: number) => Promise<void>;
  sell: (unitInstanceId: string) => Promise<void>;
  reroll: () => Promise<void>;
  toggleLock: () => Promise<void>;
  buyLevel: () => Promise<void>;
  place: (unitInstanceId: string, position: BoardPosition) => Promise<void>;
  bench: (unitInstanceId: string) => Promise<void>;
  pickAugment: (augmentId: string) => Promise<void>;
  startCombat: () => Promise<void>;
}

function run<T>(set: (partial: Partial<RunStoreState>) => void, fn: () => Promise<RunState>) {
  return fn()
    .then((run) => set({ run, error: null }))
    .catch((err) => set({ error: err instanceof ApiError ? err.message : String(err) }));
}

export const useRunStore = create<RunStoreState>((set, get) => ({
  run: null,
  units: {},
  tags: {},
  augments: {},
  lastCombat: null,
  loading: false,
  error: null,

  loadContent: async () => {
    const [units, tags, augments] = await Promise.all([api.getUnits(), api.getTags(), api.getAugmentDefs()]);
    set({
      units: Object.fromEntries(units.map((u) => [u.id, u])),
      tags: Object.fromEntries(tags.map((t) => [t.id, t])),
      augments: Object.fromEntries(augments.map((a) => [a.id, a])),
    });
  },

  loadOrCreateRun: async () => {
    set({ loading: true });
    try {
      const run = await api.getCurrentRun();
      set({ run, loading: false });
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        const run = await api.createRun();
        set({ run, loading: false });
      } else {
        set({ error: err instanceof Error ? err.message : String(err), loading: false });
      }
    }
  },

  buy: (offerIndex) => {
    const { run: current } = get();
    if (!current) return Promise.resolve();
    return run(set, () => api.buy(current.runId, offerIndex));
  },

  sell: (unitInstanceId) => {
    const { run: current } = get();
    if (!current) return Promise.resolve();
    return run(set, () => api.sell(current.runId, unitInstanceId));
  },

  reroll: () => {
    const { run: current } = get();
    if (!current) return Promise.resolve();
    return run(set, () => api.reroll(current.runId));
  },

  toggleLock: () => {
    const { run: current } = get();
    if (!current) return Promise.resolve();
    return run(set, () => api.toggleLock(current.runId));
  },

  buyLevel: () => {
    const { run: current } = get();
    if (!current) return Promise.resolve();
    return run(set, () => api.buyLevel(current.runId));
  },

  place: (unitInstanceId, position) => {
    const { run: current } = get();
    if (!current) return Promise.resolve();
    return run(set, () => api.place(current.runId, unitInstanceId, position));
  },

  bench: (unitInstanceId) => {
    const { run: current } = get();
    if (!current) return Promise.resolve();
    return run(set, () => api.bench(current.runId, unitInstanceId));
  },

  pickAugment: (augmentId) => {
    const { run: current } = get();
    if (!current) return Promise.resolve();
    return run(set, () => api.pickAugment(current.runId, augmentId));
  },

  startCombat: async () => {
    const { run: current } = get();
    if (!current) return;
    set({ loading: true });
    try {
      const result = await api.startCombat(current.runId);
      set({
        run: result.run,
        lastCombat: {
          combatLog: result.combatLog,
          winner: result.winner,
          opponentName: result.opponentName,
          opponentAvatarUrl: result.opponentAvatarUrl,
          opponentAugmentsPicked: result.opponentAugmentsPicked,
        },
        loading: false,
      });
      useAuthStore.getState().refreshProfile(); // elo changed server-side
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false });
    }
  },
}));
