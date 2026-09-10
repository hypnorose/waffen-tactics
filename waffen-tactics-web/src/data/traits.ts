export interface TraitDescriptionSource {
  threshold_descriptions?: unknown
}

export const MISSING_TRAIT_DESCRIPTION = 'Brak opisu dla tego poziomu'

const UNRESOLVED_PLACEHOLDER = /<[^>]+>/

/**
 * Reads the already-resolved description supplied by the game-data API.
 *
 * Placeholder interpolation belongs to the backend canonical data path. The
 * UI deliberately fails visibly when that contract is not met instead of
 * inventing a second resolver or showing raw template syntax to players.
 */
export function getTraitThresholdDescription(
  trait: TraitDescriptionSource,
  index: number,
): string {
  const description = Array.isArray(trait.threshold_descriptions)
    ? trait.threshold_descriptions[index]
    : undefined

  if (
    typeof description !== 'string' ||
    description.trim().length === 0 ||
    UNRESOLVED_PLACEHOLDER.test(description)
  ) {
    return MISSING_TRAIT_DESCRIPTION
  }

  return description
}
