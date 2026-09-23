import { getAffectedCells, samePosition } from '@reforged/schema';
import type { Board, BoardPosition, UnitDef } from '@reforged/schema';

export interface PositionalModifiers {
  attackPercent: number;
  attackSpeedPercent: number;
  /** 1 normally; 2 when at least one matching double-trigger source applies. */
  triggerMultiplier: number;
  /** Additive — fires as slow_enemy_team_attack_speed on this unit's own on_trigger cadence. */
  slowOnAttackPercent: number;
  /** Flat shield pulse granted on this unit's own on_trigger cadence. */
  shieldOnTriggerAmount: number;
  /** Personal Strength stacks from a positional bonus. */
  strengthStacks: number;
  appliedBonusIds: string[];
}

export interface PositionalParticipant {
  instanceId: string;
  unitId: string;
  position: BoardPosition;
}

/**
 * Resolves every unit's positionalBonus once, against the frozen board, at
 * combat start (units never move or die mid-fight, so this never needs to
 * re-run). Positional effects resolve into per-unit stat or trigger modifiers;
 * the engine applies those modifiers on the affected unit's own cadence.
 */
export function resolvePositionalBonuses(
  units: PositionalParticipant[],
  unitDefs: Record<string, UnitDef>,
): Record<string, PositionalModifiers> {
  const board: Board = units.map((u) => ({ position: u.position, unitInstanceId: u.instanceId }));
  const instanceById = new Map(units.map((u) => [u.instanceId, u]));

  const modifiers: Record<string, PositionalModifiers> = {};
  for (const u of units) {
    modifiers[u.instanceId] = {
      attackPercent: 0,
      attackSpeedPercent: 0,
      triggerMultiplier: 1,
      slowOnAttackPercent: 0,
      shieldOnTriggerAmount: 0,
      strengthStacks: 0,
      appliedBonusIds: [],
    };
  }

  for (const source of units) {
    const bonus = unitDefs[source.unitId]?.positionalBonus;
    if (!bonus) continue;

    const tagFilterMatches = bonus.tagFilter
      ? (unitInstanceId: string) => {
          const target = instanceById.get(unitInstanceId);
          const targetDef = target ? unitDefs[target.unitId] : undefined;
          return !!targetDef && bonus.tagFilter!.some((tag) => targetDef.tags.includes(tag));
        }
      : undefined;

    const affectedCells = getAffectedCells(bonus.shape, source.position, board, tagFilterMatches);
    if (bonus.effect.kind === 'grant_strength_per_adjacent_ally') {
      const sourceMod = modifiers[source.instanceId];
      if (sourceMod) {
        sourceMod.strengthStacks += Math.min(
          bonus.effect.maxStacks,
          affectedCells.length * bonus.effect.stacksPerAlly,
        );
        if (!sourceMod.appliedBonusIds.includes(bonus.id)) sourceMod.appliedBonusIds.push(bonus.id);
      }
      continue;
    }

    for (const cell of affectedCells) {
      const slot = board.find((s) => samePosition(s.position, cell));
      const targetInstanceId = slot?.unitInstanceId;
      if (!targetInstanceId) continue;
      const mod = modifiers[targetInstanceId];
      if (!mod) continue;

      if (bonus.effect.kind === 'buff_attack') mod.attackPercent += bonus.effect.percent;
      if (bonus.effect.kind === 'buff_attack_speed') mod.attackSpeedPercent += bonus.effect.percent;
      if (bonus.effect.kind === 'double_trigger') mod.triggerMultiplier = 2;
      if (bonus.effect.kind === 'grant_slow_on_attack') mod.slowOnAttackPercent += bonus.effect.percent;
      if (bonus.effect.kind === 'grant_shield_on_trigger') mod.shieldOnTriggerAmount += bonus.effect.amount;
      if (bonus.effect.kind === 'grant_strength_stacks') mod.strengthStacks += bonus.effect.stacks;
      // Multiple sources may share the same authored bonus (for example two
      // Yossarians). Keep the event contract free of duplicate effect IDs.
      if (!mod.appliedBonusIds.includes(bonus.id)) mod.appliedBonusIds.push(bonus.id);
    }
  }

  return modifiers;
}
