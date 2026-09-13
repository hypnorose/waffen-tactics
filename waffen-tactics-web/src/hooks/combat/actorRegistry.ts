export type CombatActorAnchor = HTMLDivElement

export interface CombatActorRegistry {
  register: (unitId: string, anchor: CombatActorAnchor | null) => (() => void)
  getAnchor: (unitId: string) => CombatActorAnchor | null
}

/**
 * Keeps the canonical unit id bound to the current visual card anchor.
 *
 * The disposer returned by register is identity-safe: a stale card cleanup
 * cannot remove a newer anchor registered for the same canonical unit.
 */
export function createCombatActorRegistry(): CombatActorRegistry {
  const anchors = new Map<string, CombatActorAnchor>()

  const register = (unitId: string, anchor: CombatActorAnchor | null) => {
    const normalizedId = unitId.trim()
    if (!normalizedId) return () => undefined

    if (!anchor) {
      anchors.delete(normalizedId)
      return () => undefined
    }

    anchors.set(normalizedId, anchor)
    return () => {
      if (anchors.get(normalizedId) === anchor) anchors.delete(normalizedId)
    }
  }

  const getAnchor = (unitId: string) => anchors.get(unitId.trim()) ?? null

  return { register, getAnchor }
}
