import type { UnitDef } from '@reforged/schema';
import type { UnitBuffState, UnitRuntimeSnapshot } from '../../hooks/combat/useCombatSnapshot.js';
import { rarityClass } from '../../lib/unitStyle.js';
import { StatusText } from '../../lib/statusText.js';

interface Props {
  unit: UnitRuntimeSnapshot;
  unitDef?: UnitDef;
  currentTime: number;
  justAttacked: boolean;
  justTriggeredAbility: boolean;
  buffs?: UnitBuffState;
}

export function UnitChargeBar({ unit, unitDef, currentTime, justAttacked, justTriggeredAbility, buffs }: Props) {
  const elapsed = currentTime - unit.lastAttackAt;
  const fraction = unit.attackIntervalSec !== null ? Math.max(0, Math.min(1, elapsed / unit.attackIntervalSec)) : 1;

  const classes = ['unit-charge'];
  if (unitDef) classes.push(rarityClass(unitDef.cost));
  if (justAttacked) classes.push('pulse-attack');
  if (justTriggeredAbility) classes.push('pulse-ability');

  return (
    <div className="unit-charge-wrapper">
      <div className={classes.join(' ')} title={unitDef?.name}>
        {unitDef?.avatar ? (
          <img className="unit-charge-avatar" src={unitDef.avatar} alt="" />
        ) : (
          <div className="unit-charge-emoji">{unitDef?.emoji ?? '❔'}</div>
        )}
        {unit.attackIntervalSec !== null && (
          <div className="unit-charge-track">
            <div className="unit-charge-fill" style={{ width: `${fraction * 100}%` }} />
          </div>
        )}
      </div>
      {buffs && (buffs.attackPercent !== 0 || buffs.attackSpeedPercent !== 0 || buffs.strengthStacks !== 0) && (
        <div className="unit-buff-row">
          {buffs.attackPercent !== 0 && (
            <span
              className={`unit-buff-chip combat-chip-with-tooltip ${buffs.attackPercent > 0 ? 'is-buff' : 'is-debuff'}`}
              title={`Atak: ${buffs.attackPercent > 0 ? '+' : ''}${Math.round(buffs.attackPercent)}%`}
            >
              ⚔️ {buffs.attackPercent > 0 ? '+' : ''}
              {Math.round(buffs.attackPercent)}%
              <span className="combat-chip-tooltip" role="tooltip">
                <strong>Atak: {buffs.attackPercent > 0 ? '+' : ''}{Math.round(buffs.attackPercent)}%</strong>
                <span>Łączny modyfikator obrażeń tej jednostki.</span>
              </span>
            </span>
          )}
          {buffs.attackSpeedPercent !== 0 && (
            <span
              className={`unit-buff-chip combat-chip-with-tooltip status-haste ${buffs.attackSpeedPercent > 0 ? 'is-buff' : 'is-debuff'}`}
              title={`Przyspieszenie: ${buffs.attackSpeedPercent > 0 ? '+' : ''}${Math.round(buffs.attackSpeedPercent)}%`}
            >
              💨 {buffs.attackSpeedPercent > 0 ? '+' : ''}
              {Math.round(buffs.attackSpeedPercent)}%
              <span className="combat-chip-tooltip" role="tooltip">
                <strong>Przyspieszenie: {buffs.attackSpeedPercent > 0 ? '+' : ''}{Math.round(buffs.attackSpeedPercent)}%</strong>
                <span>Dodatnia wartość skraca cooldown ataku lub aktywacji.</span>
              </span>
            </span>
          )}
          {buffs.strengthStacks !== 0 && (
            <span
              className="unit-buff-chip combat-chip-with-tooltip is-buff status-strength"
              title={'Siła: +' + Math.round(buffs.strengthStacks) + '% ataku'}
            >
              💪 +{Math.round(buffs.strengthStacks)}
              <span className="combat-chip-tooltip" role="tooltip">
                <strong>Siła: +{Math.round(buffs.strengthStacks)}%</strong>
                <span><StatusText text="Każdy stack Siły daje +1% ataku tej jednostce." /></span>
              </span>
            </span>
          )}
        </div>
      )}
      {unit.triggerMultiplier > 1 && (
        <div className="unit-buff-row">
          <span className="unit-buff-chip combat-chip-with-tooltip is-buff" title="Synergia pozycyjna: ×2 triggery.">
            ✨ ×{unit.triggerMultiplier} triggers
            <span className="combat-chip-tooltip" role="tooltip">
              <strong>Synergia pozycyjna: ×{unit.triggerMultiplier}</strong>
              <span>Każdy trigger tej jednostki uruchamia jej efekt dodatkową liczbę razy.</span>
            </span>
          </span>
        </div>
      )}
    </div>
  );
}
