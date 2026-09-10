// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import CombatUnitCard from '../CombatUnitCard'

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
  id: 'unit-1',
  name: 'Test unit',
  hp: 80,
  max_hp: 100,
  attack: 10,
  defense: 5,
  star_level: 1,
  cost: 1,
  factions: [],
  classes: [],
  avatar: '/avatars/test.png',
  current_mana: 40,
  max_mana: 100,
}

describe('CombatEffectBadge', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  const renderUnit = (effect: Record<string, unknown>, currentTime = 1) => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatUnitCard as any, {
        unit: { ...baseUnit, effects: [effect] },
        currentTime,
      }))
    })
    return container
  }

  it('shows canonical active details and remaining duration on hover', () => {
    const container = renderUnit({
      id: 'buff-1',
      type: 'buff',
      description: '+1 DEF na trafienie.',
      source: 'fap_folder',
      target: 'owner',
      scope: 'self',
      value: 0.5,
      expiresAt: 4,
      stacks: 2,
      stack_cap: 30,
    })

    const badge = container.querySelector('[data-effect-badge="buff-1-0"]') as HTMLButtonElement
    act(() => badge.dispatchEvent(new MouseEvent('mouseover', { bubbles: true })))

    expect(document.body.textContent).toContain('+1 DEF na trafienie.')
    expect(document.body.textContent).toContain('Pozostało: 3 s')
    expect(document.body.textContent).toContain('Stacki: 2/30')
    expect(document.body.textContent).toContain('Źródło: fap_folder')
  })

  it('reports an expired canonical effect without removing it locally', () => {
    const container = renderUnit({ id: 'expired-1', type: 'stun', description: 'Ogłuszenie.', expiresAt: 4 }, 4)
    const badge = container.querySelector('[data-effect-badge="expired-1-0"]') as HTMLButtonElement

    act(() => badge.focus())

    expect(document.body.textContent).toContain('Status: wygasł')
    expect(container.querySelector('[data-effect-badge="expired-1-0"]')).not.toBeNull()
  })

  it('states explicitly when the canonical effect has no description', () => {
    const container = renderUnit({ id: 'missing-description', type: 'buff' })
    const badge = container.querySelector('[data-effect-badge="missing-description-0"]') as HTMLButtonElement

    act(() => badge.focus())

    expect(document.body.textContent).toContain('Brak kanonicznego opisu tego efektu.')
  })

  it('opens from keyboard focus with a stable accessible label', () => {
    const container = renderUnit({ id: 'focus-1', type: 'shield', description: 'Tarcza 10.' })
    const badge = container.querySelector('[data-effect-badge="focus-1-0"]') as HTMLButtonElement

    expect(badge.getAttribute('aria-label')).toContain('Tarcza')
    act(() => badge.focus())

    expect(badge.getAttribute('aria-expanded')).toBe('true')
    expect(document.querySelector('[role="tooltip"]')).not.toBeNull()
  })
})
