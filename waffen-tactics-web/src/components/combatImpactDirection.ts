export type CombatImpactDirection = 'from-top' | 'from-bottom' | 'from-left' | 'from-right'

interface Point {
  x: number
  y: number
}

function isFinitePoint(point: Point | null | undefined): point is Point {
  return point !== null
    && point !== undefined
    && Number.isFinite(point.x)
    && Number.isFinite(point.y)
}

/**
 * Resolve the side from which an impact arrived without changing logical card
 * positions. The fallback keeps older events without a canonical source
 * anchor visually stable.
 */
export function getCombatImpactDirection(
  source: Point | null | undefined,
  target: Point | null | undefined,
  fallback: CombatImpactDirection,
): CombatImpactDirection {
  if (!isFinitePoint(source) || !isFinitePoint(target)) return fallback

  const dx = target.x - source.x
  const dy = target.y - source.y
  if (dx === 0 && dy === 0) return fallback

  if (Math.abs(dx) > Math.abs(dy)) return dx > 0 ? 'from-left' : 'from-right'
  return dy > 0 ? 'from-top' : 'from-bottom'
}
