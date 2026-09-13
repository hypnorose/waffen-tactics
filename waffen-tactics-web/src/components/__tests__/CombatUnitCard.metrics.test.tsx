// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import CombatUnitCard from '../CombatUnitCard'
import UnitCard from '../UnitCard'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const mockGetCenter = vi.hoisted(() => vi.fn())

vi.mock('../../hooks/useUnitAnchors', () => ({
  useUnitAnchors: () => ({ register: vi.fn(), getCenter: mockGetCenter }),
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
  shield: 12,
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
    mockGetCenter.mockReset()
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

  it('shows only bars on the combat card and keeps full metrics in the tooltip', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatUnitCard as any, { unit: combatUnit }))
    })

    expect(container.querySelector('[data-combat-vital="hp"] .combat-unit-card-vital-heading')).toBeNull()
    expect(container.querySelector('[data-combat-vital="mana"] .combat-unit-card-vital-heading')).toBeNull()
    expect(container.querySelector('[data-combat-vital="shield"]')).toBeNull()
    expect(container.querySelector('.combat-unit-card-meter-shield')).not.toBeNull()
    expect(container.querySelectorAll('[role="progressbar"]')).toHaveLength(2)
    expect(container.querySelector('.combat-unit-card')?.textContent).not.toContain('HP')
    expect(container.querySelector('.combat-unit-card')?.textContent).not.toContain('Mana')

    const card = container.querySelector('.combat-unit-card') as HTMLElement
    act(() => card.click())

    const tooltip = document.body.querySelector('[data-combat-unit-tooltip="unit-1"]') as HTMLElement
    expect(tooltip).not.toBeNull()
    expect(tooltip.textContent).toContain('HP: 80/100')
    expect(tooltip.textContent).toContain('Shield: 12')
    expect(tooltip.textContent).toContain('Mana: 100/100')
  })

  it('renders the canonical target impact flash with directional metadata', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatUnitCard as any, {
        unit: combatUnit,
        isOpponent: true,
        presentationTracks: [{
          id: 'combat:impact:target',
          intent: 'target_recoil',
          targetId: 'unit-1',
          sourceEventId: 'combat:impact',
          sourceSeq: 12,
          startedAt: 0,
          duration: 0.16,
          intensity: 'medium',
        }],
      }))
    })

    const flash = container.querySelector('.combat-unit-impact-flash')
    expect(flash?.getAttribute('data-impact-intent')).toBe('target_recoil')
    expect(flash?.getAttribute('data-impact-direction')).toBe('from-bottom')
    expect(flash?.getAttribute('aria-hidden')).toBe('true')
  })

  it('renders melee attack feedback on a local layer without moving the card slot', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatUnitCard as any, {
        unit: combatUnit,
        isOpponent: false,
        presentationTracks: [{
          id: 'combat:attack:melee',
          intent: 'melee_lunge',
          unitId: 'unit-1',
          targetId: 'opponent-1',
          sourceEventId: 'combat:attack',
          sourceSeq: 15,
          startedAt: 0,
          duration: 0.2,
          intensity: 'medium',
        }],
      }))
    })

    const sweep = container.querySelector('.combat-unit-melee-sweep')
    expect(sweep?.getAttribute('data-attack-intent')).toBe('melee_lunge')
    expect(sweep?.getAttribute('data-attack-direction')).toBe('toward-top')
    expect(sweep?.getAttribute('aria-hidden')).toBe('true')
    expect(container.querySelector('.combat-unit-card')).not.toBeNull()
  })

  it('uses the canonical source anchor when resolving impact direction', () => {
    mockGetCenter.mockImplementation((id: string) => id === 'source-unit'
      ? { x: 20, y: 100 }
      : { x: 120, y: 100 })

    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatUnitCard as any, {
        unit: combatUnit,
        isOpponent: true,
        presentationTracks: [{
          id: 'combat:impact:source-aware',
          intent: 'target_recoil',
          unitId: 'source-unit',
          targetId: 'unit-1',
          sourceEventId: 'combat:impact-source-aware',
          sourceSeq: 14,
          startedAt: 0,
          duration: 0.16,
          intensity: 'medium',
        }],
      }))
    })

    expect(container.querySelector('.combat-unit-impact-flash')?.getAttribute('data-impact-direction')).toBe('from-left')
  })

  it('renders canonical status presentation tracks without changing unit state', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatUnitCard as any, {
        unit: combatUnit,
        presentationTracks: [{
          id: 'combat:status:stun',
          intent: 'stun',
          unitId: 'unit-1',
          sourceEventId: 'combat:stun',
          sourceSeq: 13,
          startedAt: 0,
          duration: 0.26,
          intensity: 'medium',
        }],
      }))
    })

    const flash = container.querySelector('.combat-unit-status-flash')
    expect(flash?.getAttribute('data-status-intent')).toBe('stun')
    expect(flash?.getAttribute('aria-hidden')).toBe('true')
    expect(container.querySelector('[data-combat-vital="hp"] .combat-unit-card-vital-heading')).toBeNull()
  })

  it('shows the live trait effect contract and replay trigger evidence in the tooltip', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatUnitCard as any, {
        unit: { ...combatUnit, traits: ['Konfident'] },
        synergies: { Konfident: { count: 2, tier: 1 } },
        traits: [{
          name: 'Konfident',
          type: 'on_attack',
          thresholds: [2],
          threshold_descriptions: ['Przy ataku daje drużynie premię przez 3 s.'],
          // `effects` is the alias used by the live units_init payload.
          effects: [[{
            trigger: 'on_attack',
            target: 'team',
            duration: 3,
            limit: { stacking: 'none' },
          }]],
        }],
        replayEvents: [{
          type: 'passive_triggered',
          unit_id: 'unit-1',
          passive_id: 'trait:Konfident',
          passive_name: 'Konfident',
        }],
      }))
    })

    const card = container.querySelector('.combat-unit-card') as HTMLElement
    act(() => card.dispatchEvent(new MouseEvent('click', { bubbles: true })))

    const tooltip = document.body.querySelector('[data-combat-unit-tooltip="unit-1"]') as HTMLElement
    expect(tooltip).not.toBeNull()
    expect(tooltip.textContent).toContain('Konfident')
    expect(tooltip.textContent).toContain('✓ Aktywny T1')
    expect(tooltip.textContent).toContain('Przy ataku daje drużynie premię przez 3 s.')
    expect(tooltip.textContent).toContain('Trigger: Przy ataku')
    expect(tooltip.textContent).toContain('Cel: Cały zespół')
    expect(tooltip.textContent).toContain('Czas: 3 s')
    expect(tooltip.textContent).toContain('Zadziałał w replayu: 1 trigger')
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
