import { unitHpContribution, type UnitDef } from '@reforged/schema';

/** No mana, no defense in Reforged. Attack/attack speed are optional — a pure support unit shows neither. */
export function UnitStatRow({ unitDef }: { unitDef: UnitDef }) {
  return (
    <div className="unit-stat-row">
      {unitDef.baseStats.attack !== undefined && (
        <span className="unit-stat" title="Obrażenia ataku">
          ⚔️ {unitDef.baseStats.attack}
        </span>
      )}
      {unitDef.baseStats.attacksPerSecond !== undefined && (
        <span className="unit-stat" title="Ataki (lub aktywacje) na sekundę">
          ⏱️ {unitDef.baseStats.attacksPerSecond}
        </span>
      )}
      <span className="unit-stat" title="Wkład w pulę HP drużyny">
        ❤️ {unitHpContribution(unitDef.cost)}
      </span>
    </div>
  );
}
