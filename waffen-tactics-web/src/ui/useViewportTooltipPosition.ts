import { useCallback, useEffect, useLayoutEffect, useRef, useState, type RefObject } from 'react'

export type ViewportTooltipPlacement = 'above' | 'below'

export interface ViewportTooltipPosition {
  left: number
  top: number
  placement: ViewportTooltipPlacement
}

export interface ViewportTooltipSize {
  width: number
  height: number
}

export interface ViewportTooltipViewport {
  width: number
  height: number
}

export interface ViewportTooltipAnchor {
  left: number
  right: number
  top: number
  bottom: number
  width: number
}

const clamp = (value: number, minimum: number, maximum: number) => Math.min(Math.max(value, minimum), maximum)

/**
 * Calculate a fixed tooltip position that stays within the viewport.
 *
 * The same calculation is shared by every tooltip family. Individual
 * components still own their content and visual variant, but they no longer
 * drift in edge handling or listener lifecycle.
 */
export function getViewportTooltipPosition(
  anchor: ViewportTooltipAnchor,
  viewport: ViewportTooltipViewport,
  size: ViewportTooltipSize,
  margin = 8,
): ViewportTooltipPosition {
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
  const placement: ViewportTooltipPlacement = availableBelow >= tooltipHeight || availableBelow >= availableAbove ? 'below' : 'above'
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

interface UseViewportTooltipPositionOptions {
  open: boolean
  anchorRef?: RefObject<HTMLElement | null>
  anchor?: HTMLElement | null
  size: ViewportTooltipSize
  measuredRef?: RefObject<HTMLElement | null>
  margin?: number
}

interface UseViewportTooltipPositionResult {
  position: ViewportTooltipPosition | null
  updatePosition: () => void
}

/**
 * Owns the lifecycle for a viewport tooltip position.
 *
 * `measuredRef` is optional. When a tooltip has long or dynamic content, the
 * hook uses its real rendered dimensions on the next layout pass and clamps
 * again. This keeps portals usable on narrow screens without guessing in
 * every component.
 */
export function useViewportTooltipPosition({
  open,
  anchorRef,
  anchor,
  size,
  measuredRef,
  margin = 8,
}: UseViewportTooltipPositionOptions): UseViewportTooltipPositionResult {
  const [position, setPosition] = useState<ViewportTooltipPosition | null>(null)
  const measuredOnOpen = useRef(false)
  const width = size.width
  const height = size.height

  const updatePosition = useCallback(() => {
    if (typeof window === 'undefined') return

    const resolvedAnchor = anchor ?? anchorRef?.current
    if (!resolvedAnchor) return

    const measured = measuredRef?.current?.getBoundingClientRect()
    const measuredSize = measured && measured.width > 0 && measured.height > 0
      ? { width: measured.width, height: measured.height }
      : { width, height }

    setPosition(getViewportTooltipPosition(
      resolvedAnchor.getBoundingClientRect(),
      { width: window.innerWidth, height: window.innerHeight },
      measuredSize,
      margin,
    ))
  }, [anchor, anchorRef, height, margin, measuredRef, width])

  const useSafeLayoutEffect = typeof window === 'undefined' ? useEffect : useLayoutEffect

  useSafeLayoutEffect(() => {
    if (!open) {
      measuredOnOpen.current = false
      setPosition(null)
      return
    }

    updatePosition()
  }, [open, updatePosition])

  useEffect(() => {
    // A tooltip helper can live in a child while its anchor ref belongs to a
    // parent. In that case the layout pass may precede the parent's ref
    // attachment; retry once after the commit, but only while no position
    // exists so this cannot loop.
    if (!open || position !== null) return
    updatePosition()
  }, [open, position !== null, updatePosition])

  useSafeLayoutEffect(() => {
    // The first pass may happen before a conditional portal is mounted. Run
    // one more measurement after the position enables that portal so long
    // tooltip content gets its real dimensions without creating a loop.
    if (!open || position === null || measuredOnOpen.current) return
    measuredOnOpen.current = true
    updatePosition()
  }, [open, position !== null, updatePosition])

  useEffect(() => {
    if (!open || typeof window === 'undefined') return

    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)

    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [open, updatePosition])

  return { position, updatePosition }
}
