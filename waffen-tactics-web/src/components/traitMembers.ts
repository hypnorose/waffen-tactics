export interface TraitMemberUnit {
  traits?: unknown
}

/**
 * Resolve trait membership from the canonical unit projection returned by the
 * game-data API. Legacy factions/classes are intentionally not consulted:
 * they are separate metadata and cannot silently redefine Set 2 membership.
 */
export function getUnitsForTrait<T extends TraitMemberUnit>(
  units: readonly T[],
  traitName: string,
): T[] {
  if (!traitName.trim()) return []

  return units.filter((unit) => (
    Array.isArray(unit.traits)
    && unit.traits.some((trait) => trait === traitName)
  ))
}
