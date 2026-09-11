// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import ItemsPanel from '../ItemsPanel'
import { getRecipePreview } from '../../data/items'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

vi.mock('../../services/api', () => ({
  gameAPI: {
    getItems: vi.fn().mockResolvedValue({
      data: [{ id: 'spices', name: 'Przyprawy', kind: 'base', stats: { attack: 5 } }],
    }),
    combineItem: vi.fn(),
  },
}))

describe('ItemsPanel tooltip ownership', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  it('renders only one tooltip when repeated inventory entries share an item id', async () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    await act(async () => {
      root = createRoot(container)
      root.render(
        <ItemsPanel
          playerState={{ item_inventory: ['spices', 'spices'] } as any}
          onUpdate={vi.fn()}
          onNotification={vi.fn()}
        />,
      )
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    const itemEntries = container.querySelectorAll('[aria-label="Przyprawy"]')
    expect(itemEntries).toHaveLength(2)

    await act(async () => {
      itemEntries[0].dispatchEvent(new MouseEvent('mouseover', { bubbles: true }))
      await Promise.resolve()
    })

    const tooltip = document.body.querySelector('[data-item-tooltip]') as HTMLElement
    expect(document.body.querySelectorAll('[data-item-tooltip]')).toHaveLength(1)
    expect(tooltip.parentElement).toBe(document.body)
    expect(tooltip.style.position).toBe('fixed')
    expect(tooltip.style.zIndex).toBe('2000')
  })

  it('renders canonical names, stats, and descriptions from the API catalog', async () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    await act(async () => {
      root = createRoot(container)
      root.render(
        <ItemsPanel
          itemCatalog={[{
            id: 'etf_przyprawowy',
            name: 'ETF przyprawowy',
            kind: 'combined',
            components: ['spices', 'spices'],
            stats: { attack: 30 },
            description: '+30 ataku.',
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
          playerState={{ item_inventory: ['etf_przyprawowy'] } as any}
          onUpdate={vi.fn()}
          onNotification={vi.fn()}
        />,
      )
      await Promise.resolve()
    })

    const itemEntry = container.querySelector('[aria-label^="ETF przyprawowy"]')
    expect(itemEntry).not.toBeNull()
    expect(itemEntry?.getAttribute('aria-label')).toContain('+30 ataku.')

    await act(async () => {
      itemEntry?.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }))
      await Promise.resolve()
    })

    expect(document.body.textContent).toContain('ETF przyprawowy')
    expect(document.body.textContent).toContain('Obrażenia')
    expect(document.body.textContent).toContain('+30 Obrażenia')
    expect(document.body.textContent).toContain('+30 ataku.')
    expect(document.body.textContent).toContain('Aktywacja: Przy ataku')
    expect(document.body.textContent).toContain('Czas działania: 2 s')
    expect(document.body.textContent).toContain('Stacki: maks. 10')
  })

  it('places a top-row tooltip below the item instead of under the sticky navbar', async () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    await act(async () => {
      root = createRoot(container)
      root.render(
        <ItemsPanel
          itemCatalog={[{ id: 'spices', name: 'Przyprawy', kind: 'base', stats: { attack: 5 } } as any]}
          playerState={{ item_inventory: ['spices'] } as any}
          onUpdate={vi.fn()}
          onNotification={vi.fn()}
        />,
      )
      await Promise.resolve()
    })

    const itemEntry = container.querySelector('[aria-label="Przyprawy"]') as HTMLElement
    vi.spyOn(itemEntry, 'getBoundingClientRect').mockReturnValue({
      top: 88,
      bottom: 136,
      left: 100,
      right: 148,
      width: 48,
      height: 48,
      x: 100,
      y: 88,
      toJSON: () => ({}),
    })

    await act(async () => {
      itemEntry.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }))
      await Promise.resolve()
    })

    expect(document.body.querySelector('[data-tooltip-placement="below"]')).not.toBeNull()
  })

  it('shows an explicit stale-id state instead of inventing an item definition', async () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    await act(async () => {
      root = createRoot(container)
      root.render(
        <ItemsPanel
          itemCatalog={[]}
          playerState={{ item_inventory: ['legacy_item_id'] } as any}
          onUpdate={vi.fn()}
          onNotification={vi.fn()}
        />,
      )
      await Promise.resolve()
    })

    const stale = container.querySelector('[data-item-state="stale"]')
    expect(stale).not.toBeNull()
    expect(stale?.getAttribute('aria-label')).toBe('Nieznany przedmiot: legacy_item_id')
    expect(container.textContent).toContain('Nieznany przedmiot: legacy_item_id')
  })

  it('previews only exact unordered canonical recipe pairs', () => {
    const catalog = [
      { id: 'spices_safe', kind: 'combined', components: ['spices', 'safe'], name: 'Skrytka', } as any,
      { id: 'spices_spices', kind: 'combined', components: ['spices', 'spices'], name: 'ETF', } as any,
    ]

    expect(getRecipePreview(catalog, 'safe', 'spices')?.id).toBe('spices_safe')
    expect(getRecipePreview(catalog, 'spices', 'spices')?.id).toBe('spices_spices')
    expect(getRecipePreview(catalog, 'safe', 'coat')).toBeUndefined()
  })
})
