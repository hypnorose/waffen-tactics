import { unitHpContribution, type UnitDef } from '@reforged/schema';
import { unitEffectIcon } from '../../lib/unitStyle.js';

/**
 * No mana, no defense in Reforged. Attack/cadence are optional — a pure
 * support unit (no attack stat) shows its one effect's icon in place of the
 * damage number, and the action cooldown alongside it.
 */
function formatCooldown(attacksPerSecond: number): string {
  const cooldown = 1 / attacksPerSecond;
  return `${cooldown.toFixed(2).replace(/\.?(0+)$/, '')} s`;
}

export function UnitStatRow({ unitDef }: { unitDef: UnitDef }) {
  const supportIcon = unitDef.baseStats.attack === undefined ? unitEffectIcon(unitDef) : null;

  return (
    <div className="unit-stat-row">
      {unitDef.baseStats.attack !== undefined && (
        <span className="unit-stat" title="Obrażenia ataku">
          ⚔️ {unitDef.baseStats.attack}
        </span>
      )}
      {supportIcon && (
        <span className="unit-stat" title="Efekt wspierający (jednostka nie zadaje obrażeń)">
          {supportIcon}
        </span>
      )}
      {unitDef.baseStats.attacksPerSecond !== undefined && (
        <span className="unit-stat" title="Cooldown ataku lub aktywacji">
          ⏱️ {formatCooldown(unitDef.baseStats.attacksPerSecond)}
        </span>
      )}
      <span className="unit-stat" title="Wkład w pulę HP drużyny">
        ❤️ {unitHpContribution(unitDef.cost)}
      </span>
    </div>
  );
}
