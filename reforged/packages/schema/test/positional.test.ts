import { describe, expect, it } from 'vitest';
import { emptyBoard, getAffectedCells, type Board } from '../src/index.js';

function boardWithUnitsAt(positions: Array<{ row: number; col: number; id: string }>): Board {
  const board = emptyBoard();
  for (const { row, col, id } of positions) {
    const slot = board.find((s) => s.position.row === row && s.position.col === col);
    if (slot) slot.unitInstanceId = id;
  }
  return board;
}

describe('getAffectedCells', () => {
  it('self shape only affects the anchor cell', () => {
    const board = boardWithUnitsAt([{ row: 1, col: 1, id: 'a' }]);
    expect(getAffectedCells('self', { row: 1, col: 1 }, board)).toEqual([{ row: 1, col: 1 }]);
  });

  it('cross shape affects orthogonal neighbors only', () => {
    const board = boardWithUnitsAt([
      { row: 1, col: 1, id: 'center' },
      { row: 0, col: 1, id: 'up' },
      { row: 2, col: 1, id: 'down' },
      { row: 1, col: 0, id: 'left' },
      { row: 1, col: 2, id: 'right' },
      { row: 0, col: 0, id: 'corner' },
    ]);
    const affected = getAffectedCells('cross', { row: 1, col: 1 }, board);
    expect(affected).toHaveLength(4);
    expect(affected).not.toContainEqual({ row: 0, col: 0 });
  });

  it('adjacent shape includes diagonals but not the anchor itself', () => {
    const board = boardWithUnitsAt([
      { row: 1, col: 1, id: 'center' },
      { row: 0, col: 0, id: 'corner' },
      { row: 2, col: 2, id: 'farCorner' },
    ]);
    const affected = getAffectedCells('adjacent', { row: 1, col: 1 }, board);
    expect(affected).toContainEqual({ row: 0, col: 0 });
    expect(affected).not.toContainEqual({ row: 1, col: 1 });
  });

  it('row/column shapes ignore empty cells', () => {
    const board = boardWithUnitsAt([{ row: 0, col: 2, id: 'ally' }]);
    expect(getAffectedCells('row', { row: 0, col: 0 }, board)).toEqual([{ row: 0, col: 2 }]);
    expect(getAffectedCells('column', { row: 1, col: 2 }, board)).toEqual([{ row: 0, col: 2 }]);
  });

  it('tagFilter excludes non-matching units', () => {
    const board = boardWithUnitsAt([
      { row: 0, col: 1, id: 'tagged' },
      { row: 2, col: 1, id: 'untagged' },
    ]);
    const affected = getAffectedCells('column', { row: 1, col: 1 }, board, (id) => id === 'tagged');
    expect(affected).toEqual([{ row: 0, col: 1 }]);
  });
});
