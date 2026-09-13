// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, useRef } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { useViewportTooltipPosition } from '../useViewportTooltipPosition'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

function TooltipPositionProbe() {
  const anchorRef = useRef<HTMLDivElement | null>(null)
  const { position } = useViewportTooltipPosition({
    open: true,
    anchorRef,
    size: { width: 240, height: 160 },
  })

  return <div ref={anchorRef} data-tooltip-position={position ? `${position.left}:${position.top}:${position.placement}` : ''} />
}

describe('shared viewport tooltip positioning', () => {
  let root: Root | null = null

  afterEach(() => {
    act(() => root?.unmount())
    root = null
    document.body.replaceChildren()
  })

  it('repositions the portal anchor through the shared resize lifecycle', () => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 800 })
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 600 })

    const container = document.createElement('div')
    document.body.appendChild(container)
    act(() => {
      root = createRoot(container)
      root.render(<TooltipPositionProbe />)
    })

    const anchor = container.querySelector('[data-tooltip-position]') as HTMLDivElement
    expect(anchor.dataset.tooltipPosition).toMatch(/:below$/)

    vi.spyOn(anchor, 'getBoundingClientRect').mockReturnValue({
      left: 720,
      right: 800,
      top: 520,
      bottom: 600,
      width: 80,
      height: 80,
      x: 720,
      y: 520,
      toJSON: () => ({}),
    } as DOMRect)

    act(() => window.dispatchEvent(new Event('resize')))

    const [left, top, placement] = (anchor.dataset.tooltipPosition || '').split(':')
    expect(Number(left)).toBeGreaterThanOrEqual(8)
    expect(Number(left) + 240).toBeLessThanOrEqual(792)
    expect(Number(top)).toBeGreaterThanOrEqual(8)
    expect(Number(top) + 160).toBeLessThanOrEqual(592)
    expect(placement).toBe('above')
  })
})
