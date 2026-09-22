import { TagSchema, UnitDefSchema, type Tag, type UnitDef } from '@reforged/schema';
import { tagsData } from './tags.data.js';
import { unitsData } from './units.data.js';
import { unitOverrides } from './overrides.js';

let cachedUnits: Record<string, UnitDef> | null = null;
let cachedTags: Tag[] | null = null;

function assertUniqueAbilityIds(
  unitId: string,
  abilities: UnitDef['startOfCombat'],
  phase: string,
  seen: Set<string>,
  allAbilityIds: Set<string>,
): void {
  if (!abilities) return;
  for (const ability of abilities) {
    if (seen.has(ability.id)) throw new Error(`Duplicate ${phase} ability "${ability.id}" on unit "${unitId}"`);
    if (allAbilityIds.has(ability.id)) throw new Error(`Duplicate ability "${ability.id}" in unit content`);
    seen.add(ability.id);
    allAbilityIds.add(ability.id);
  }
}

/** Fail-closed: throws with the offending unit id if content doesn't validate. */
export function getUnitDefs(): Record<string, UnitDef> {
  if (cachedUnits) return cachedUnits;

  const result: Record<string, UnitDef> = {};
  const positionalBonusIds = new Set<string>();
  const allAbilityIds = new Set<string>();
  for (const entry of unitsData) {
    const merged = { ...entry, ...unitOverrides[entry.id] };
    const parsed = UnitDefSchema.safeParse(merged);
    if (!parsed.success) {
      throw new Error(`Invalid unit content for "${entry.id}": ${parsed.error.message}`);
    }
    const abilityIdsForUnit = new Set<string>();
    assertUniqueAbilityIds(parsed.data.id, parsed.data.startOfCombat, 'start_of_combat', abilityIdsForUnit, allAbilityIds);
    assertUniqueAbilityIds(parsed.data.id, parsed.data.onTrigger, 'onTrigger', abilityIdsForUnit, allAbilityIds);
    if (parsed.data.positionalBonus) {
      if (positionalBonusIds.has(parsed.data.positionalBonus.id)) {
        throw new Error(`Duplicate positional bonus "${parsed.data.positionalBonus.id}"`);
      }
      positionalBonusIds.add(parsed.data.positionalBonus.id);
    }
    result[parsed.data.id] = parsed.data;
  }

  cachedUnits = result;
  return result;
}

export function getUnitList(): UnitDef[] {
  return Object.values(getUnitDefs());
}

export function getTagDefs(): Tag[] {
  if (cachedTags) return cachedTags;

  cachedTags = tagsData.map((entry, index) => {
    const parsed = TagSchema.safeParse(entry);
    if (!parsed.success) {
      throw new Error(`Invalid tag content at index ${index}: ${parsed.error.message}`);
    }
    return parsed.data;
  });
  return cachedTags;
}
