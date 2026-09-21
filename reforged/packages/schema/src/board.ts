import { z } from 'zod';

export const BOARD_SIZE = 3;

export const BoardPositionSchema = z.object({
  row: z.number().int().min(0).max(2),
  col: z.number().int().min(0).max(2),
});
export type BoardPosition = z.infer<typeof BoardPositionSchema>;

export const BoardSlotSchema = z.object({
  position: BoardPositionSchema,
  unitInstanceId: z.string().nullable(),
});
export type BoardSlot = z.infer<typeof BoardSlotSchema>;

export const BoardSchema = z.array(BoardSlotSchema).length(9);
export type Board = z.infer<typeof BoardSchema>;

export function samePosition(a: BoardPosition, b: BoardPosition): boolean {
  return a.row === b.row && a.col === b.col;
}

export function emptyBoard(): Board {
  const slots: BoardSlot[] = [];
  for (let row = 0; row < BOARD_SIZE; row++) {
    for (let col = 0; col < BOARD_SIZE; col++) {
      slots.push({ position: { row, col }, unitInstanceId: null });
    }
  }
  return slots;
}
