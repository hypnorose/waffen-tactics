export type CombatTooltipPlacement = 'above' | 'below'

export interface CombatTooltipPosition {
  left: number
  top: number
  placement: CombatTooltipPlacement
}

export interface CombatTooltipViewport {
  width: number
  height: number
}

export interface CombatTooltipSize {
  width: number
  height: number
}

const clamp = (value: number, minimum: number, maximum: number) => Math.min(Math.max(value, minimum), maximum)

/**
 * Positions a fixed combat tooltip so its estimated box stays inside the viewport.
 * The actual tooltip can be shorter than the estimate, but never exceeds the same
 * viewport-constrained max-height in CombatUnitCard.
 */
export function getCombatTooltipPosition(
  anchor: Pick<DOMRect, 'left' | 'right' | 'top' | 'bottom' | 'width'>,
  viewport: CombatTooltipViewport,
  size: CombatTooltipSize = { width: 320, height: 360 },
  margin = 8,
): CombatTooltipPosition {
  const availableWidth = Math.max(0, viewport.width - margin * 2)
  const tooltipWidth = Math.min(size.width, availableWidth)
  const minLeft = margin
  const maxLeft = Math.max(minLeft, viewport.width - tooltipWidth - margin)
  const anchorCenter = anchor.left + (anchor.width || anchor.right - anchor.left) / 2
  const left = clamp(anchorCenter - tooltipWidth / 2, minLeft, maxLeft)

  const availableHeight = Math.max(0, viewport.height - margin * 2)
  const tooltipHeight = Math.min(size.height, availableHeight)
  const availableAbove = anchor.top - margin
  const availableBelow = viewport.height - anchor.bottom - margin
  const placement: CombatTooltipPlacement = availableBelow >= tooltipHeight || availableBelow >= availableAbove ? 'below' : 'above'
  const desiredTop = placement === 'below'
    ? anchor.bottom + margin
    : anchor.top - tooltipHeight - margin
  const minTop = margin
  const maxTop = Math.max(minTop, viewport.height - tooltipHeight - margin)

  return {
    left,
    top: clamp(desiredTop, minTop, maxTop),
    placement,
  }
}
