import { emptyBoard, samePosition, type Board, type BoardPosition, type RunState } from '@reforged/schema';
import { maxBoardUnits } from './economyService.js';

export class UnitInstanceNotFoundError extends Error {}
export class BoardCapacityError extends Error {}

/** Placing onto an occupied slot swaps the two units; placing from the bench onto one sends the occupant to the bench. */
export function place(run: RunState, unitInstanceId: string, position: BoardPosition): RunState {
  const instance = run.units.find((u) => u.instanceId === unitInstanceId);
  if (!instance) throw new UnitInstanceNotFoundError();

  const sourceSlot = run.board.find((slot) => slot.unitInstanceId === unitInstanceId);
  if (sourceSlot && samePosition(sourceSlot.position, position)) return run;

  const targetSlot = run.board.find((slot) => samePosition(slot.position, position));
  const occupantId = targetSlot?.unitInstanceId ?? null;

  if (!sourceSlot && !occupantId) {
    const currentlyPlaced = run.board.filter((slot) => slot.unitInstanceId !== null).length;
    if (currentlyPlaced >= maxBoardUnits(run.level)) {
      throw new BoardCapacityError();
    }
  }

  return {
    ...run,
    board: run.board.map((slot) => {
      if (samePosition(slot.position, position)) return { ...slot, unitInstanceId };
      if (sourceSlot && samePosition(slot.position, sourceSlot.position)) return { ...slot, unitInstanceId: occupantId };
      return slot;
    }),
  };
}

/** Fills a fresh board row-major, used to seat a bot opponent's roster for combat. */
export function autoPlaceOnBoard(instanceIds: string[]): Board {
  const board = emptyBoard();
  instanceIds.slice(0, board.length).forEach((instanceId, i) => {
    board[i].unitInstanceId = instanceId;
  });
  return board;
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
