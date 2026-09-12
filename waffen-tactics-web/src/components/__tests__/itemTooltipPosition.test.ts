import { describe, expect, it } from 'vitest'
import { getItemTooltipPosition } from '../itemTooltipPosition'

describe('item tooltip positioning', () => {
  it('keeps the tooltip inside every viewport edge and flips vertically when needed', () => {
    const viewport = { width: 360, height: 240 }
    const size = { width: 256, height: 180 }
    const edges = [
      { left: 0, right: 48, top: 80, bottom: 128, width: 48 },
      { left: 312, right: 360, top: 80, bottom: 128, width: 48 },
      { left: 156, right: 204, top: 0, bottom: 48, width: 48 },
      { left: 156, right: 204, top: 192, bottom: 240, width: 48 },
    ]

    for (const edge of edges) {
      const position = getItemTooltipPosition(edge, viewport, size)
      expect(position.left).toBeGreaterThanOrEqual(8)
      expect(position.left + size.width).toBeLessThanOrEqual(viewport.width - 8)
      expect(position.top).toBeGreaterThanOrEqual(8)
      expect(position.top + size.height).toBeLessThanOrEqual(viewport.height - 8)
    }

    expect(getItemTooltipPosition(edges[2], viewport, size).placement).toBe('below')
    expect(getItemTooltipPosition(edges[3], viewport, size).placement).toBe('above')
  })

  it('shrinks the measured box for a compact viewport instead of overflowing horizontally', () => {
    const position = getItemTooltipPosition(
      { left: 0, right: 24, top: 40, bottom: 64, width: 24 },
      { width: 120, height: 160 },
      { width: 256, height: 220 },
    )

    expect(position.left).toBe(8)
    expect(position.left + 104).toBe(112)
    expect(position.top).toBeGreaterThanOrEqual(8)
    expect(position.top + 144).toBeLessThanOrEqual(152)
  })
})
