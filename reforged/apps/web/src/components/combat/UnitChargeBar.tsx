import type { UnitDef } from '@reforged/schema';
import type { UnitRuntimeSnapshot } from '../../hooks/combat/useCombatSnapshot.js';

interface Props {
  unit: UnitRuntimeSnapshot;
  unitDef?: UnitDef;
  currentTime: number;
  justAttacked: boolean;
  justTriggeredAbility: boolean;
}

export function UnitChargeBar({ unit, unitDef, currentTime, justAttacked, justTriggeredAbility }: Props) {
  const elapsed = currentTime - unit.lastAttackAt;
  const fraction = unit.attackIntervalSec > 0 ? Math.max(0, Math.min(1, elapsed / unit.attackIntervalSec)) : 1;

  const classes = ['unit-charge'];
  if (justAttacked) classes.push('pulse-attack');
  if (justTriggeredAbility) classes.push('pulse-ability');

  return (
    <div className={classes.join(' ')} title={unitDef?.name}>
      {unitDef?.avatar ? (
        <img className="unit-charge-avatar" src={unitDef.avatar} alt="" />
      ) : (
        <div className="unit-charge-emoji">{unitDef?.emoji ?? '❔'}</div>
      )}
      <div className="unit-charge-track">
        <div className="unit-charge-fill" style={{ width: `${fraction * 100}%` }} />
      </div>
    </div>
  );
}
