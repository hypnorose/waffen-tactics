import { describe, expect, it } from 'vitest'
import { combatUnitCardOpponentSizingStyle, combatUnitCardSizingStyle } from '../combatUnitCardLayout'
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

  it('uses CSS sizing variables so short viewports can compact combat cards only', () => {
    expect(combatUnitCardSizingStyle.width).toBe('var(--combat-unit-card-width, 120px)')
    expect(combatUnitCardSizingStyle.padding).toBe('var(--combat-unit-card-padding, 0.5rem)')
    expect(combatUnitCardSizingStyle.avatarHeight).toBe('var(--combat-unit-avatar-height, 60px)')
    expect(combatUnitCardSizingStyle.barHeight).toBe('var(--combat-unit-bar-height, 0.5rem)')
    expect(combatUnitCardSizingStyle.barGap).toBe('var(--combat-unit-bar-gap, 0.25rem)')
    expect(combatUnitCardOpponentSizingStyle.padding).toBe('var(--combat-unit-card-padding-opponent, 0.25rem)')
  })
})
