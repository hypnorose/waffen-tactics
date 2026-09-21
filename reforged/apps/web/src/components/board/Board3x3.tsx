import { useState } from 'react';
import type { RunState, UnitDef, UnitInstance } from '@reforged/schema';
import { BoardCell } from './BoardCell.js';
import { getHighlightedPositions, isHighlighted } from './PositionalBonusOverlay.js';

interface Props {
  run: RunState;
  units: Record<string, UnitDef>;
}

export function Board3x3({ run, units }: Props) {
  const [hoveredInstanceId, setHoveredInstanceId] = useState<string | null>(null);
  const unitByInstanceId: Record<string, UnitInstance> = Object.fromEntries(run.units.map((u) => [u.instanceId, u]));
  const highlighted = getHighlightedPositions(run.board, hoveredInstanceId, unitByInstanceId, units);

  return (
    <div className="board-3x3">
      {run.board.map((slot) => {
        const instance = slot.unitInstanceId ? unitByInstanceId[slot.unitInstanceId] : undefined;
        return (
          <BoardCell
            key={`${slot.position.row}-${slot.position.col}`}
            slot={slot}
            unitInstance={instance}
            unitDef={instance ? units[instance.unitId] : undefined}
            highlighted={isHighlighted(highlighted, slot.position)}
            onHoverUnit={setHoveredInstanceId}
          />
        );
      })}
    </div>
  );
}
