import type { AugmentDef } from '@reforged/schema';
import { StatusText } from '../../lib/statusText.js';

interface Props {
  augment: AugmentDef;
  onPick: () => void;
}

export function AugmentCard({ augment, onPick }: Props) {
  return (
    <button className={`augment-card tier-${augment.tier}`} onClick={onPick}>
      <div className="augment-icon">{augment.icon}</div>
      <div className="augment-tier">{augment.tier.toUpperCase()}</div>
      <div className="augment-name">{augment.name}</div>
      <div className="augment-desc"><StatusText text={augment.description} /></div>
    </button>
  );
}
