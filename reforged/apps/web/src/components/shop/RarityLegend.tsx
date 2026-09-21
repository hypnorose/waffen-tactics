import { shopOddsForLevel } from '@reforged/schema';

const RARITY_LABEL = ['1', '2', '3', '4', '5'];

/** Shows which rarities (cost tiers) are actually available in the shop at the player's current level, and their odds. */
export function RarityLegend({ level }: { level: number }) {
  const odds = shopOddsForLevel(level);
  const total = odds.reduce((sum, o) => sum + o, 0);

  return (
    <div className="rarity-legend">
      {RARITY_LABEL.map((label, i) => {
        const percent = total > 0 ? Math.round((odds[i] / total) * 100) : 0;
        return (
          <span key={label} className={`rarity-chip rarity-${i + 1}${percent === 0 ? ' is-unavailable' : ''}`}>
            {label}★ {percent}%
          </span>
        );
      })}
    </div>
  );
}
