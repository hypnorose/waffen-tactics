import { TagSchema, UnitDefSchema, type Tag, type UnitDef } from '@reforged/schema';
import { tagsData } from './tags.data.js';
import { unitsData } from './units.data.js';
import { unitOverrides } from './overrides.js';

let cachedUnits: Record<string, UnitDef> | null = null;
let cachedTags: Tag[] | null = null;

/** Fail-closed: throws with the offending unit id if content doesn't validate. */
export function getUnitDefs(): Record<string, UnitDef> {
  if (cachedUnits) return cachedUnits;

  const result: Record<string, UnitDef> = {};
  for (const entry of unitsData) {
    const merged = { ...entry, ...unitOverrides[entry.id] };
    const parsed = UnitDefSchema.safeParse(merged);
    if (!parsed.success) {
      throw new Error(`Invalid unit content for "${entry.id}": ${parsed.error.message}`);
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
