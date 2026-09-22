import type { AugmentDef } from '@reforged/schema';

interface Props {
  augment: AugmentDef;
}

export function AugmentIcon({ augment }: Props) {
  return (
    <div className={`augment-chip tier-${augment.tier}`}>
      <span className="augment-chip-icon">{augment.icon}</span>
      <div className="augment-chip-tooltip">
        <div className="augment-chip-tooltip-title">{augment.name}</div>
        <div className="augment-chip-tooltip-tier">{augment.tier.toUpperCase()}</div>
        <p className="augment-chip-tooltip-desc">{augment.description}</p>
      </div>
    </div>
  );
}
