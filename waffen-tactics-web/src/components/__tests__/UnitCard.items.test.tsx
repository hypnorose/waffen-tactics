// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import UnitCard from '../UnitCard'
import { getUnitItemPreview } from '../../data/items'

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

const previewCatalog = [
  { id: 'spices', name: 'Przyprawy', kind: 'base', components: [], stats: { attack: 5 }, effect: null, content_version: 'test' },
  { id: 'safe', name: 'Sejf', kind: 'base', components: [], stats: { defense: 3 }, effect: null, content_version: 'test' },
  { id: 'skrytka', name: 'Skrytka na oregano', kind: 'combined', components: ['spices', 'safe'], stats: { attack: 12, defense: 7 }, description: '+12 ataku, +7 obrony, trafiony przeciwnik ma -30% obrony przez 2 s.', effect: null, content_version: 'test' },
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

  it('renders a portal preview for a unit target without changing equipped items', async () => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    const preview = getUnitItemPreview(previewCatalog, ['spices'], 'safe')

    await act(async () => {
      root = createRoot(container)
      root.render(
        <UnitCard
          unitId="preview-unit"
          detailed
          items={['spices']}
          itemCatalog={previewCatalog}
          baseStats={{ attack: 10, defense: 5, hp: 100, attack_speed: 1, max_mana: 100 }}
          itemPreview={preview ?? undefined}
        />,
      )
      await Promise.resolve()
    })

    const previewNode = document.body.querySelector('[data-item-preview]')
    expect(previewNode).not.toBeNull()
    expect(previewNode?.textContent).toContain('Podgląd wyposażenia')
    expect(previewNode?.textContent).toContain('Sejf')
    expect(previewNode?.textContent).toContain('Wyposażenie po operacji')
    expect(container.querySelectorAll('[data-item-state]')).toHaveLength(1)
  })

  it('uses the generated result stat rows once in the unit item preview', async () => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    const preview = getUnitItemPreview(previewCatalog, ['spices'], 'skrytka')

    await act(async () => {
      root = createRoot(container)
      root.render(
        <UnitCard
          unitId="preview-unit"
          detailed
          items={['spices']}
          itemCatalog={previewCatalog}
          itemPreview={preview ?? undefined}
        />,
      )
      await Promise.resolve()
    })

    const previewText = document.body.querySelector('[data-item-preview]')?.textContent || ''
    expect(previewText.match(/\+12 Obrażenia/g)).toHaveLength(1)
    expect(previewText.match(/\+7 Obrona/g)).toHaveLength(1)
    expect(previewText).not.toContain('+12 ataku')
    expect(previewText).not.toContain('+7 obrony')
    expect(previewText).toContain('trafiony przeciwnik ma -30% obrony przez 2 s.')
  })

  it('uses the same board shell height and neutral reserved slots for every item count', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(
        <>
          <UnitCard unitId="long-unit" boardLayout items={[]} itemCatalog={itemCatalog} />
          <UnitCard unitId="long-unit" boardLayout items={['item-1']} itemCatalog={itemCatalog} />
          <UnitCard unitId="long-unit" boardLayout items={['item-1', 'item-2', 'item-3']} itemCatalog={itemCatalog} />
        </>,
      )
    })

    const cards = Array.from(container.querySelectorAll('[data-board-unit-card="true"]'))
    expect(cards).toHaveLength(3)
    expect(new Set(cards.map((card) => (card as HTMLElement).style.height))).toEqual(new Set(['var(--board-unit-card-height-compact, 10rem)']))
    expect(container.querySelectorAll('.board-unit-card-faction-slot')).toHaveLength(3)
    expect(container.querySelectorAll('.board-unit-card-items-slot')).toHaveLength(3)
    expect(container.querySelectorAll('.board-unit-card-items-slot[aria-hidden="true"]')).toHaveLength(1)
    expect(container.textContent).toContain('Bardzo długi nick jednostki testowej')
  })
})
