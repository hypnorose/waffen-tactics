import { describe, expect, it } from 'vitest'
import { combatOverlayBoardStyle, combatOverlayPanelStyle, combatOverlaySidebarStyle } from '../combatOverlayLayout'

describe('combat overlay layout contract', () => {
  it('clamps the combat panel to the viewport instead of using an overflowing fixed frame', () => {
    expect(combatOverlayPanelStyle.width).toBe('min(1400px, calc(100vw - 16px))')
    expect(combatOverlayPanelStyle.height).toBe('min(850px, calc(100vh - 16px))')
    expect(combatOverlayPanelStyle.maxWidth).toBe('calc(100vw - 16px)')
    expect(combatOverlayPanelStyle.maxHeight).toBe('calc(100vh - 16px)')
    expect(combatOverlayPanelStyle.boxSizing).toBe('border-box')
    expect(combatOverlayPanelStyle.overflow).toBe('hidden')
  })

  it('keeps the summary column scrollable and the board column shrinkable', () => {
    expect(combatOverlaySidebarStyle.overflowY).toBe('auto')
    expect(combatOverlaySidebarStyle.minHeight).toBe(0)
    expect(combatOverlayBoardStyle.minWidth).toBe(0)
    expect(combatOverlayBoardStyle.minHeight).toBe(0)
  })
})
