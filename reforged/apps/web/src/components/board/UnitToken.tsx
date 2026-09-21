import { useDraggable } from '@dnd-kit/core';
import type { UnitDef } from '@reforged/schema';
import { rarityClass, tagClass } from '../../lib/unitStyle.js';
import { UnitAbilityTooltip } from './UnitAbilityTooltip.js';

interface Props {
  instanceId: string;
  unitDef: UnitDef;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
}

export function UnitToken({ instanceId, unitDef, onMouseEnter, onMouseLeave }: Props) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: instanceId,
    data: { unitId: unitDef.id },
  });
  const style = transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`, zIndex: 10 } : undefined;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={`unit-token ${rarityClass(unitDef.cost)}${isDragging ? ' is-dragging' : ''}`}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      title={unitDef.name}
    >
      {unitDef.avatar ? (
        <img className="unit-avatar" src={unitDef.avatar} alt="" />
      ) : (
        <div className="unit-emoji">{unitDef.emoji}</div>
      )}
      <div className="unit-name">{unitDef.name}</div>
      <div className="unit-tags">
        {unitDef.tags.map((tag) => (
          <span key={tag} className={`unit-tag ${tagClass(tag)}`}>
            {tag}
          </span>
        ))}
      </div>
      <UnitAbilityTooltip unitDef={unitDef} />
    </div>
  );
}
