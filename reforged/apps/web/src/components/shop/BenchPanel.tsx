import { useDroppable } from '@dnd-kit/core';
import { getBenchedUnits, type RunState, type UnitDef } from '@reforged/schema';
import { UnitToken } from '../board/UnitToken.js';

interface Props {
  run: RunState;
  units: Record<string, UnitDef>;
  onSell: (instanceId: string) => void;
}

export function BenchPanel({ run, units, onSell }: Props) {
  const { setNodeRef, isOver } = useDroppable({ id: 'bench' });
  const benched = getBenchedUnits(run);

  return (
    <div ref={setNodeRef} className={`bench-panel${isOver ? ' is-over' : ''}`}>
      <h3>Ławka ({benched.length}/9)</h3>
      <div className="bench-units">
        {benched.map((instance) => {
          const def = units[instance.unitId];
          if (!def) return null;
          return (
            <div key={instance.instanceId} className="bench-slot">
              <UnitToken instanceId={instance.instanceId} unitDef={def} />
              <button className="sell-button" onClick={() => onSell(instance.instanceId)}>
                Sprzedaj ({def.cost}g)
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
