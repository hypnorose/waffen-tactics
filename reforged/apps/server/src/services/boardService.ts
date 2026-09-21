import { samePosition, type BoardPosition, type RunState } from '@reforged/schema';
import { maxBoardUnits } from './economyService.js';

export class UnitInstanceNotFoundError extends Error {}
export class SlotOccupiedError extends Error {}
export class BoardCapacityError extends Error {}

export function place(run: RunState, unitInstanceId: string, position: BoardPosition): RunState {
  const instance = run.units.find((u) => u.instanceId === unitInstanceId);
  if (!instance) throw new UnitInstanceNotFoundError();

  const targetSlot = run.board.find((slot) => samePosition(slot.position, position));
  if (targetSlot?.unitInstanceId && targetSlot.unitInstanceId !== unitInstanceId) {
    throw new SlotOccupiedError();
  }

  const currentlyPlaced = run.board.filter((slot) => slot.unitInstanceId !== null).length;
  const alreadyOnBoard = run.board.some((slot) => slot.unitInstanceId === unitInstanceId);
  if (!alreadyOnBoard && currentlyPlaced >= maxBoardUnits(run.level)) {
    throw new BoardCapacityError();
  }

  return {
    ...run,
    board: run.board.map((slot) => {
      if (slot.unitInstanceId === unitInstanceId) return { ...slot, unitInstanceId: null };
      if (samePosition(slot.position, position)) return { ...slot, unitInstanceId };
      return slot;
    }),
  };
}

export function bench(run: RunState, unitInstanceId: string): RunState {
  const instance = run.units.find((u) => u.instanceId === unitInstanceId);
  if (!instance) throw new UnitInstanceNotFoundError();

  return {
    ...run,
    board: run.board.map((slot) =>
      slot.unitInstanceId === unitInstanceId ? { ...slot, unitInstanceId: null } : slot,
    ),
  };
}
