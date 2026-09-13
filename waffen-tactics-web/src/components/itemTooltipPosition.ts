import {
  getViewportTooltipPosition,
  type ViewportTooltipPosition,
  type ViewportTooltipSize,
  type ViewportTooltipViewport,
} from '../ui/useViewportTooltipPosition'

export type ItemTooltipPlacement = 'above' | 'below'
export type ItemTooltipPosition = ViewportTooltipPosition
export type ItemTooltipViewport = ViewportTooltipViewport
export type ItemTooltipSize = ViewportTooltipSize

/** Backwards-compatible item alias for the shared viewport calculation. */
export function getItemTooltipPosition(
  anchor: Pick<DOMRect, 'left' | 'right' | 'top' | 'bottom' | 'width'>,
  viewport: ItemTooltipViewport,
  size: ItemTooltipSize = { width: 256, height: 300 },
  margin = 8,
): ItemTooltipPosition {
  return getViewportTooltipPosition(anchor, viewport, size, margin)
}
