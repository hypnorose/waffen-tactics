import { randomUUID } from 'node:crypto';
import { getBenchedUnits, type RunState, type UnitInstance } from '@reforged/schema';
import { getUnitDefs, getUnitList } from '@reforged/content-data';
import { MAX_BENCH_SIZE, REROLL_COST, rollShopOffers } from './economyService.js';

export class InsufficientGoldError extends Error {}
export class BenchFullError extends Error {}
export class InvalidShopOfferError extends Error {}
export class UnitInstanceNotFoundError extends Error {}

export function reroll(run: RunState): RunState {
  if (run.gold < REROLL_COST) throw new InsufficientGoldError();
  return {
    ...run,
    gold: run.gold - REROLL_COST,
    shopOffers: rollShopOffers(run.level, getUnitList()),
  };
}

export function toggleLock(run: RunState): RunState {
  return { ...run, shopLocked: !run.shopLocked };
}

export function buy(run: RunState, offerIndex: number): RunState {
  const unitId = run.shopOffers[offerIndex];
  if (!unitId) throw new InvalidShopOfferError();

  const def = getUnitDefs()[unitId];
  if (!def) throw new InvalidShopOfferError();
  if (run.gold < def.cost) throw new InsufficientGoldError();
  if (getBenchedUnits(run).length >= MAX_BENCH_SIZE) throw new BenchFullError();

  const instance: UnitInstance = { instanceId: randomUUID(), unitId, starLevel: 1 };
  const shopOffers = [...run.shopOffers];
  shopOffers[offerIndex] = null;

  return {
    ...run,
    gold: run.gold - def.cost,
    units: [...run.units, instance],
    shopOffers,
  };
}

export function sell(run: RunState, unitInstanceId: string): RunState {
  const instance = run.units.find((u) => u.instanceId === unitInstanceId);
  if (!instance) throw new UnitInstanceNotFoundError();

  const def = getUnitDefs()[instance.unitId];
  const refund = def?.cost ?? 0;

  return {
    ...run,
    gold: run.gold + refund,
    units: run.units.filter((u) => u.instanceId !== unitInstanceId),
    board: run.board.map((slot) =>
      slot.unitInstanceId === unitInstanceId ? { ...slot, unitInstanceId: null } : slot,
    ),
  };
}
