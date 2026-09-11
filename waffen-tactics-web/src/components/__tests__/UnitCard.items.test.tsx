// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import UnitCard from '../UnitCard'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

vi.mock('../../data/units', () => ({
  getCostBorderColor: () => '#6b7280',
  getFactionColor: () => 'bg-slate-500',
  getPassiveTitle: () => null,
  getUnit: (unitId: string) => ({
    id: unitId,
    name: unitId === 'long-unit' ? 'Bardzo długi nick jednostki testowej' : `Unit ${unitId}`,
    cost: 2,
    factions: ['Faction'],
    classes: ['Class'],
    avatar: '',
    stats: { hp: 100, attack: 10, defense: 5, attack_speed: 1, max_mana: 100 },
  }),
}))

const itemCatalog = [
  { id: 'item-1', name: 'Item 1', kind: 'base', stats: { attack: 5 } },
  { id: 'item-2', name: 'Item 2', kind: 'base', stats: { defense: 5 } },
  { id: 'item-3', name: 'Item 3', kind: 'base', stats: { hp: 5 } },
] as any

describe('UnitCard equipped item layout', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  it.each([
    { itemCount: 0, compactHeight: 'min-h-36', detailedHeight: 'min-h-64' },
    { itemCount: 1, compactHeight: 'min-h-40', detailedHeight: 'min-h-72' },
    { itemCount: 3, compactHeight: 'min-h-40', detailedHeight: 'min-h-72' },
  ])('keeps the nickname and item row visible for $itemCount equipped items', ({ itemCount, compactHeight, detailedHeight }) => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    const items = itemCatalog.slice(0, itemCount).map((item: any) => item.id)

    act(() => {
      root = createRoot(container)
      root.render(
        <>
          <UnitCard unitId="long-unit" detailed={false} items={items} itemCatalog={itemCatalog} />
          <UnitCard unitId="long-unit" detailed items={items} itemCatalog={itemCatalog} />
        </>,
      )
    })

    const headings = Array.from(container.querySelectorAll('h3'))
    expect(headings).toHaveLength(2)
    for (const heading of headings) {
      expect(heading.textContent).toContain('Bardzo długi nick jednostki testowej')
      expect(heading.getAttribute('title')).toBe('Bardzo długi nick jednostki testowej')
      expect(heading.getAttribute('aria-label')).toBe('Jednostka: Bardzo długi nick jednostki testowej')
    }

    expect(headings[0].parentElement?.className).toContain(compactHeight)
    expect(headings[1].parentElement?.className).toContain(detailedHeight)
    expect(container.querySelectorAll('[data-item-state]')).toHaveLength(itemCount * 2)
  })
})
