// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import CombatUnitCard from '../CombatUnitCard'
import UnitCard from '../UnitCard'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

vi.mock('../../hooks/useUnitAnchors', () => ({
  useUnitAnchors: () => ({ register: vi.fn() }),
}))

vi.mock('../../data/units', () => ({
  getCostBorderColor: () => '#6b7280',
  getFactionColor: () => 'bg-slate-500',
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

const roundStats = {
  participated: true,
  damage_dealt: 24,
  damage_received: 12,
  active_seconds: 2,
  avg_dps: 12,
  avg_damage_received: 6,
}

const combatUnit = {
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
  current_mana: 100,
  max_mana: 100,
}

const tableUnitStats = {
  hp: 100,
  attack: 10,
  defense: 5,
  attack_speed: 1,
  max_mana: 100,
  current_mana: 0,
}

describe('combat and table unit metric ownership', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  it('keeps DPS, received-per-second metrics, and the old BONUS badge off the combat card', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatUnitCard as any, { unit: combatUnit, roundStats }))
    })

    expect(container.textContent).not.toContain('DPS')
    expect(container.textContent).not.toContain('Przyjęte/s')
    expect(container.textContent).not.toContain('BONUS')

    act(() => {
      container.firstElementChild?.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }))
    })

    expect(container.textContent).not.toContain('DPS')
    expect(container.textContent).not.toContain('Przyjęte/s')
    expect(container.textContent).not.toContain('BONUS')
  })

  it('keeps the same metrics available on the between-battle table card', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(
        <UnitCard
          unitId="unit-1"
          detailed={false}
          baseStats={tableUnitStats}
          lastRoundStats={roundStats}
        />,
      )
    })

    expect(container.textContent).toContain('DPS 12.0')
    expect(container.textContent).toContain('-HP/s 6.0')
  })

  it('shows canonical item details and an explicit stale id in the unit tooltip', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(
        <UnitCard
          unitId="unit-1"
          items={['etf_przyprawowy', 'legacy_item_id']}
          itemCatalog={[{
            id: 'etf_przyprawowy',
            name: 'ETF przyprawowy',
            kind: 'combined',
            components: ['spices', 'spices'],
            stats: { attack: 30 },
            effect: {
              family: 'per_attack_stack',
              description: '+30 ataku.',
              trigger: 'on_attack',
              target: 'owner',
              scope: 'self',
              order: 'stat/shield application',
              duration: 2,
              stacking: { mode: 'additive', max_stacks: 10 },
              cap: 10,
              reset_between_fights: true,
              rng: { mode: 'none', seed: 'test-seed' },
              replay: { mode: 'canonical_event', event_types: ['stat_buff'] },
            },
            content_version: 'wft139-approved-2026-09-10',
          }] as any}
        />,
      )
    })

    const card = container.querySelector('[aria-label="Jednostka: Test unit"]') as HTMLElement
    act(() => card.dispatchEvent(new MouseEvent('click', { bubbles: true })))

    const tooltip = document.body.querySelector('[data-unit-tooltip="unit-1"]') as HTMLElement
    expect(tooltip).not.toBeNull()
    expect(tooltip.textContent).toContain('ETF przyprawowy')
    expect(tooltip.textContent).toContain('+30 Obrażenia')
    expect(tooltip.textContent).not.toContain('+30 ataku.')
    expect(tooltip.textContent).toContain('Aktywacja: Przy ataku · 2 s')
    expect(tooltip.textContent).toContain('Nieznany przedmiot: legacy_item_id')
  })
})
