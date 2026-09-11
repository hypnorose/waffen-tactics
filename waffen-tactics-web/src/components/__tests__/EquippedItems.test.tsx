// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import EquippedItems from '../EquippedItems'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('EquippedItems canonical catalog presentation', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  it('shows canonical names and an explicit state for stale equipped IDs', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(
        <EquippedItems
          itemIds={['etf_przyprawowy', 'legacy_item_id']}
          itemCatalog={[{
            id: 'etf_przyprawowy',
            name: 'ETF przyprawowy',
            kind: 'combined',
            components: ['spices', 'spices'],
            stats: { attack: 30 },
            effect: null,
            content_version: 'wft139-approved-2026-09-10',
          }] as any}
        />,
      )
    })

    expect(container.querySelector('[aria-label="ETF przyprawowy"]')).not.toBeNull()
    expect(container.querySelector('[data-item-state="stale"]')?.getAttribute('title'))
      .toBe('Nieznany przedmiot: legacy_item_id')
  })

  it('renders the known item tooltip above the card in a body portal', async () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(
        <EquippedItems
          itemIds={['etf_przyprawowy']}
          itemCatalog={[{
            id: 'etf_przyprawowy',
            name: 'ETF przyprawowy',
            kind: 'combined',
            components: ['spices', 'spices'],
            stats: { attack: 30 },
            effect: null,
            content_version: 'wft139-approved-2026-09-10',
          }] as any}
        />,
      )
    })

    const item = container.querySelector('[aria-label="ETF przyprawowy"]') as HTMLElement
    act(() => item.dispatchEvent(new MouseEvent('mouseover', { bubbles: true })))

    const tooltip = document.body.querySelector('[data-item-tooltip]') as HTMLElement
    expect(tooltip).not.toBeNull()
    expect(tooltip.parentElement).toBe(document.body)
    expect(tooltip.style.zIndex).toBe('2000')
    expect(tooltip.textContent).toContain('ETF przyprawowy')
  })
})
