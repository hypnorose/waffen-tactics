import type { UnitDef } from '@reforged/schema';
import type { UnitBuffState, UnitRuntimeSnapshot } from '../../hooks/combat/useCombatSnapshot.js';
import { rarityClass } from '../../lib/unitStyle.js';

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
      {buffs && (buffs.attackPercent !== 0 || buffs.attackSpeedPercent !== 0) && (
        <div className="unit-buff-row">
          {buffs.attackPercent !== 0 && (
            <span className={`unit-buff-chip ${buffs.attackPercent > 0 ? 'is-buff' : 'is-debuff'}`}>
              ⚔️ {buffs.attackPercent > 0 ? '+' : ''}
              {Math.round(buffs.attackPercent)}%
            </span>
          )}
          {buffs.attackSpeedPercent !== 0 && (
            <span className={`unit-buff-chip ${buffs.attackSpeedPercent > 0 ? 'is-buff' : 'is-debuff'}`}>
              💨 {buffs.attackSpeedPercent > 0 ? '+' : ''}
              {Math.round(buffs.attackSpeedPercent)}%
            </span>
          )}
        </div>
      )}
      {unit.triggerMultiplier > 1 && (
        <div className="unit-buff-row">
          <span className="unit-buff-chip is-buff" title="A same-trait positional synergy doubles this unit's ability triggers.">
            ✨ ×{unit.triggerMultiplier} triggers
          </span>
        </div>
      )}
    </div>
  );
}
