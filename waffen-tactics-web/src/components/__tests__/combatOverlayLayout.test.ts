import { describe, expect, it } from 'vitest'
import { combatUnitCardOpponentSizingStyle, combatUnitCardSizingStyle } from '../combatUnitCardLayout'
import { combatOverlayBoardStyle, combatOverlayPanelStyle, combatOverlaySidebarStyle, shouldStartCombatPanelCollapsed } from '../combatOverlayLayout'

describe('combat overlay layout contract', () => {
  it('clamps the combat panel to the viewport instead of using an overflowing fixed frame', () => {
    expect(combatOverlayPanelStyle.width).toBe('min(1500px, calc(100vw - 32px))')
    expect(combatOverlayPanelStyle.height).toBe('min(900px, calc(100dvh - 32px))')
    expect(combatOverlayPanelStyle.maxWidth).toBe('calc(100vw - 32px)')
    expect(combatOverlayPanelStyle.maxHeight).toBe('calc(100dvh - 32px)')
    expect(combatOverlayPanelStyle.boxSizing).toBe('border-box')
    expect(combatOverlayPanelStyle.overflow).toBe('hidden')
  })

  it('keeps the summary column scrollable and the board column shrinkable', () => {
    expect(combatOverlaySidebarStyle.overflowY).toBe('auto')
    expect(combatOverlaySidebarStyle.minHeight).toBe(0)
    expect(combatOverlayBoardStyle.minWidth).toBe(0)
    expect(combatOverlayBoardStyle.minHeight).toBe(0)
  })

  it('starts collapsed so the fight stays the primary surface at every viewport', () => {
    expect(shouldStartCombatPanelCollapsed(1280)).toBe(true)
    expect(shouldStartCombatPanelCollapsed(1920)).toBe(true)
    expect(shouldStartCombatPanelCollapsed(899)).toBe(true)
  })

  it('uses CSS sizing variables so combat cards can compact across viewports', () => {
    expect(combatUnitCardSizingStyle.width).toBe('var(--combat-unit-card-width, 6.5rem)')
    expect(combatUnitCardSizingStyle.padding).toBe('var(--combat-unit-card-padding, 0.4rem)')
    expect(combatUnitCardSizingStyle.avatarHeight).toBe('var(--combat-unit-avatar-height, auto)')
    expect(combatUnitCardSizingStyle.barHeight).toBe('var(--combat-unit-bar-height, 0.5rem)')
    expect(combatUnitCardSizingStyle.barGap).toBe('var(--combat-unit-bar-gap, 0.25rem)')
    expect(combatUnitCardOpponentSizingStyle.padding).toBe('var(--combat-unit-card-padding-opponent, 0.4rem)')
  })
})
