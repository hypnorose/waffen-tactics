// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import ItemsPanel from '../ItemsPanel'

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

    expect(container.querySelectorAll('.pointer-events-none')).toHaveLength(1)
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
            effect: null,
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

    expect(container.textContent).toContain('ETF przyprawowy')
    expect(container.textContent).toContain('Obrażenia')
    expect(container.textContent).toContain('+30 Obrażenia')
    expect(container.textContent).toContain('+30 ataku.')
  })
})
