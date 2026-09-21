import type { Board, BoardPosition } from './board.js';
import { samePosition } from './board.js';
import type { PositionalShape } from './positionalBonus.js';

/**
 * Single source of truth for "which board cells does a positional bonus affect".
 * Used by BOTH the UI hover/selection overlay and the combat engine resolver so
 * the preview can never drift from what combat actually does.
 */
export function getAffectedCells(
  shape: PositionalShape,
  anchor: BoardPosition,
  board: Board,
  tagFilterMatches?: (unitInstanceId: string) => boolean,
): BoardPosition[] {
  if (shape === 'self') {
    const anchorSlot = board.find((slot) => samePosition(slot.position, anchor));
    if (!anchorSlot?.unitInstanceId) return [];
    if (tagFilterMatches && !tagFilterMatches(anchorSlot.unitInstanceId)) return [];
    return [anchor];
  }

  const affected: BoardPosition[] = [];
  for (const slot of board) {
    if (!slot.unitInstanceId) continue;
    if (samePosition(slot.position, anchor)) continue;
    if (!inShape(shape, anchor, slot.position)) continue;
    if (tagFilterMatches && !tagFilterMatches(slot.unitInstanceId)) continue;
    affected.push(slot.position);
  }
  return affected;
}

function inShape(shape: Exclude<PositionalShape, 'self'>, anchor: BoardPosition, target: BoardPosition): boolean {
  const dRow = target.row - anchor.row;
  const dCol = target.col - anchor.col;

  switch (shape) {
    case 'adjacent':
      return Math.abs(dRow) <= 1 && Math.abs(dCol) <= 1;
    case 'cross':
      return (dRow === 0 && Math.abs(dCol) === 1) || (dCol === 0 && Math.abs(dRow) === 1);
    case 'row':
      return dRow === 0;
    case 'column':
      return dCol === 0;
  }
}
