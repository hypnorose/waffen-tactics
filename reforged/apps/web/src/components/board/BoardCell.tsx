import { useDroppable } from '@dnd-kit/core';
import type { BoardSlot, UnitDef, UnitInstance } from '@reforged/schema';
import { UnitToken } from './UnitToken.js';

interface Props {
  slot: BoardSlot;
  unitInstance?: UnitInstance;
  unitDef?: UnitDef;
  highlighted: boolean;
  onHoverUnit: (instanceId: string | null) => void;
}

export function BoardCell({ slot, unitInstance, unitDef, highlighted, onHoverUnit }: Props) {
  const { setNodeRef, isOver } = useDroppable({
    id: `cell-${slot.position.row}-${slot.position.col}`,
    data: { position: slot.position },
  });

  const classes = ['board-cell'];
  if (isOver) classes.push('is-over');
  if (highlighted) classes.push('is-highlighted');

  return (
    <div ref={setNodeRef} className={classes.join(' ')}>
      {unitInstance && unitDef && (
        <UnitToken
          instanceId={unitInstance.instanceId}
          unitDef={unitDef}
          onMouseEnter={() => onHoverUnit(unitInstance.instanceId)}
          onMouseLeave={() => onHoverUnit(null)}
        />
      )}
    </div>
  );
}
