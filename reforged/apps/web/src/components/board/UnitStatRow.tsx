import { unitHpContribution, type UnitDef } from '@reforged/schema';

/** No mana in Reforged — only attack, attack speed, defense, and the unit's HP contribution to the shared team pool. */
export function UnitStatRow({ unitDef }: { unitDef: UnitDef }) {
  return (
    <div className="unit-stat-row">
      <span className="unit-stat" title="Obrażenia ataku">
        ⚔️ {unitDef.baseStats.attack}
      </span>
      <span className="unit-stat" title="Ataki na sekundę">
        ⏱️ {unitDef.baseStats.attacksPerSecond}
      </span>
      <span className="unit-stat" title="Obrona (redukcja obrażeń)">
        🛡️ {unitDef.baseStats.defense}
      </span>
      <span className="unit-stat" title="Wkład w pulę HP drużyny">
        ❤️ {unitHpContribution(unitDef.cost)}
      </span>
    </div>
  );
}
