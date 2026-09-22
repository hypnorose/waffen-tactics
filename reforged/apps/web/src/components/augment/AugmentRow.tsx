import type { AugmentDef } from '@reforged/schema';
import { AugmentIcon } from './AugmentIcon.js';

interface Props {
  augmentIds: string[];
  augments: Record<string, AugmentDef>;
  align?: 'left' | 'right';
  label?: string;
}

export function AugmentRow({ augmentIds, augments, align, label }: Props) {
  const picked = augmentIds.map((id) => augments[id]).filter((a): a is AugmentDef => !!a);
  if (picked.length === 0) return null;

  return (
    <div className={`augment-row${align ? ` align-${align}` : ''}`}>
      {label && <span className="augment-row-label">{label}</span>}
      <div className="augment-row-icons">
        {picked.map((augment, i) => (
          // an augment id can be picked more than once? no — but the same
          // *definition* could theoretically repeat in future content, so
          // key on index+id to stay safe without assuming uniqueness.
          <AugmentIcon key={`${augment.id}-${i}`} augment={augment} />
        ))}
      </div>
    </div>
  );
}
