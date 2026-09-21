import { getAffectedCells, samePosition, type Board, type BoardPosition, type UnitDef, type UnitInstance } from '@reforged/schema';

/**
 * Reuses the exact same `getAffectedCells` the combat engine's
 * positionalResolver runs — so whatever this preview highlights is
 * guaranteed to be what combat actually buffs, by construction.
 */
export function getHighlightedPositions(
  board: Board,
  hoveredInstanceId: string | null,
  unitByInstanceId: Record<string, UnitInstance>,
  unitDefs: Record<string, UnitDef>,
): BoardPosition[] {
  if (!hoveredInstanceId) return [];
  const instance = unitByInstanceId[hoveredInstanceId];
  const def = instance ? unitDefs[instance.unitId] : undefined;
  const bonus = def?.positionalBonus;
  if (!bonus) return [];

  const anchorSlot = board.find((s) => s.unitInstanceId === hoveredInstanceId);
  if (!anchorSlot) return [];

  const tagFilterMatches = bonus.tagFilter
    ? (targetInstanceId: string) => {
        const targetInstance = unitByInstanceId[targetInstanceId];
        const targetDef = targetInstance ? unitDefs[targetInstance.unitId] : undefined;
        return !!targetDef && bonus.tagFilter!.some((tag) => targetDef.tags.includes(tag));
      }
    : undefined;

  return getAffectedCells(bonus.shape, anchorSlot.position, board, tagFilterMatches);
}

export function isHighlighted(positions: BoardPosition[], position: BoardPosition): boolean {
  return positions.some((p) => samePosition(p, position));
}
