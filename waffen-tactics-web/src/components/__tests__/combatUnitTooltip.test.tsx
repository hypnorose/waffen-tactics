// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import CombatUnitCard from '../CombatUnitCard'
import { getCombatTooltipPosition } from '../combatTooltipPosition'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

vi.mock('../../hooks/useUnitAnchors', () => ({
  useUnitAnchors: () => ({ register: vi.fn() }),
}))

vi.mock('../../data/units', () => ({
  getPassiveTitle: () => null,
  getUnit: (unitId: string) => ({
    id: unitId,
    name: 'Test unit',
    cost: 1,
    factions: [],
    classes: [],
    stats: { hp: 100, attack: 10, defense: 5, attack_speed: 1 },
  }),
}))

const baseUnit = {
  id: 'unit-tooltip-1',
  name: 'Test unit',
  hp: 80,
  max_hp: 100,
  attack: 10,
  defense: 5,
  star_level: 1,
  cost: 1,
  factions: ['Test faction'],
  classes: ['Test class'],
  avatar: '/avatars/test.png',
  current_mana: 40,
}

describe('combat unit tooltip positioning', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  it('keeps the estimated tooltip box inside the viewport at every board edge', () => {
    const viewport = { width: 800, height: 600 }
    const edges = [
      { left: 0, right: 80, top: 250, bottom: 330, width: 80 },
      { left: 720, right: 800, top: 250, bottom: 330, width: 80 },
      { left: 360, right: 440, top: 0, bottom: 80, width: 80 },
      { left: 360, right: 440, top: 520, bottom: 600, width: 80 },
    ]

    for (const edge of edges) {
      const position = getCombatTooltipPosition(edge, viewport)
      expect(position.left).toBeGreaterThanOrEqual(8)
      expect(position.left + 320).toBeLessThanOrEqual(viewport.width - 8)
      expect(position.top).toBeGreaterThanOrEqual(8)
      expect(position.top + 360).toBeLessThanOrEqual(viewport.height - 8)
    }
  })

  it('renders the unit tooltip in a fixed body portal and clamps a right-edge card', () => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 800 })
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 600 })

    const container = document.createElement('div')
    document.body.appendChild(container)
    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatUnitCard as any, { unit: baseUnit }))
    })

    const card = container.querySelector('.combat-unit-card') as HTMLDivElement
    vi.spyOn(card, 'getBoundingClientRect').mockReturnValue({
      left: 720,
      right: 800,
      top: 250,
      bottom: 330,
      width: 80,
      height: 80,
      x: 720,
      y: 250,
      toJSON: () => ({}),
    } as DOMRect)

    act(() => card.dispatchEvent(new MouseEvent('mouseover', { bubbles: true })))

    const tooltip = document.body.querySelector('[data-combat-unit-tooltip="unit-tooltip-1"]') as HTMLDivElement
    expect(tooltip).not.toBeNull()
    expect(tooltip.parentElement).toBe(document.body)
    expect(tooltip.style.position).toBe('fixed')
    expect(tooltip.style.left).toBe('472px')
    expect(tooltip.style.top).toBe('232px')
    expect(container.querySelector('[data-combat-unit-tooltip="unit-tooltip-1"]')).toBeNull()
  })
})
