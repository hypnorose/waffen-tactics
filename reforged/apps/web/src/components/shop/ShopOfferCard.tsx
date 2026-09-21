import type { UnitDef } from '@reforged/schema';

interface Props {
  unitDef?: UnitDef;
  onBuy: () => void;
  disabled: boolean;
}

export function ShopOfferCard({ unitDef, onBuy, disabled }: Props) {
  if (!unitDef) {
    return <div className="shop-offer is-empty" />;
  }

  return (
    <div className="shop-offer">
      <div className="unit-emoji">{unitDef.emoji}</div>
      <div className="unit-name">{unitDef.name}</div>
      <div className="unit-tags">
        {unitDef.tags.map((tag) => (
          <span key={tag} className="unit-tag">
            {tag}
          </span>
        ))}
      </div>
      <div className="shop-offer-cost">{unitDef.cost}g</div>
      <button onClick={onBuy} disabled={disabled}>
        Kup
      </button>
    </div>
  );
}
