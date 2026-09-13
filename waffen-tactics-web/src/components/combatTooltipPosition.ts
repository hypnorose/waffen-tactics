import {
  getViewportTooltipPosition,
  type ViewportTooltipPosition,
  type ViewportTooltipSize,
  type ViewportTooltipViewport,
} from '../ui/useViewportTooltipPosition'

export type CombatTooltipPlacement = 'above' | 'below'
export type CombatTooltipPosition = ViewportTooltipPosition
export type CombatTooltipViewport = ViewportTooltipViewport
export type CombatTooltipSize = ViewportTooltipSize

/** Backwards-compatible combat alias for the shared viewport calculation. */
export function getCombatTooltipPosition(
  anchor: Pick<DOMRect, 'left' | 'right' | 'top' | 'bottom' | 'width'>,
  viewport: CombatTooltipViewport,
  size: CombatTooltipSize = { width: 320, height: 360 },
  margin = 8,
): CombatTooltipPosition {
  return getViewportTooltipPosition(anchor, viewport, size, margin)
}
