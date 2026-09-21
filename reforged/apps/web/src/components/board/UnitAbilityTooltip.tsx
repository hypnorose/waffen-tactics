import type { UnitDef } from '@reforged/schema';

export function UnitAbilityTooltip({ unitDef }: { unitDef: UnitDef }) {
  const abilities = [...(unitDef.startOfCombat ?? []), ...(unitDef.onTrigger ?? [])];

  return (
    <div className="unit-tooltip">
      <div className="unit-tooltip-title">{unitDef.name}</div>
      <div className="unit-tooltip-tags">
        {unitDef.tags.map((tag) => (
          <span key={tag} className="unit-tag">
            {tag}
          </span>
        ))}
      </div>
      {unitDef.positionalBonus && <p className="unit-tooltip-ability">📍 {unitDef.positionalBonus.description}</p>}
      {abilities.map((ability) => (
        <p key={ability.id} className="unit-tooltip-ability">
          {ability.trigger === 'start_of_combat' && '⚡ '}
          {ability.trigger === 'on_attack' && '🗡️ '}
          {ability.trigger === 'periodic' && '🔁 '}
          {ability.trigger === 'low_team_hp' && '🩸 '}
          {ability.description}
        </p>
      ))}
      {abilities.length === 0 && !unitDef.positionalBonus && <p className="unit-tooltip-ability muted">Brak dodatkowych efektów.</p>}
    </div>
  );
}
