import { xpToNextLevel, type RunState, type UnitDef } from '@reforged/schema';
import { RarityLegend } from './RarityLegend.js';
import { ShopOfferCard } from './ShopOfferCard.js';

interface Props {
  run: RunState;
  units: Record<string, UnitDef>;
  onBuy: (offerIndex: number) => void;
  onReroll: () => void;
  onToggleLock: () => void;
  onBuyXp: () => void;
}

export function ShopPanel({ run, units, onBuy, onReroll, onToggleLock, onBuyXp }: Props) {
  const xpMax = xpToNextLevel(run.level);

  return (
    <div className="shop-panel">
      <div className="shop-header">
        <span className="gold">💰 {run.gold}</span>
        <span>
          Poziom {run.level} {xpMax !== null ? `(${run.xp}/${xpMax} XP)` : '(MAX)'}
        </span>
        <button onClick={onBuyXp} disabled={run.gold < 4}>
          Kup XP (4g)
        </button>
        <button onClick={onReroll} disabled={run.gold < 2}>
          🎲 Reroll (2g)
        </button>
        <button onClick={onToggleLock} className={run.shopLocked ? 'active' : ''}>
          {run.shopLocked ? '🔒' : '🔓'}
        </button>
      </div>
      <div className="shop-offers">
        {run.shopOffers.map((unitId, i) => {
          const unitDef = unitId ? units[unitId] : undefined;
          return (
            <ShopOfferCard
              key={i}
              unitDef={unitDef}
              onBuy={() => onBuy(i)}
              disabled={!unitDef || run.gold < unitDef.cost}
            />
          );
        })}
      </div>
      <RarityLegend level={run.level} />
    </div>
  );
}
