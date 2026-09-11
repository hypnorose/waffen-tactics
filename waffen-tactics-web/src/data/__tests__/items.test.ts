import { describe, expect, it } from 'vitest'
import { getUnitItemPreview, type Item } from '../items'

const item = (overrides: Partial<Item>): Item => ({
  id: 'item',
  name: 'Item',
  kind: 'base',
  components: [],
  stats: {},
  effect: null,
  content_version: 'test',
  ...overrides,
})

const catalog: Item[] = [
  item({ id: 'spices', name: 'Przyprawy', stats: { attack: 5 } }),
  item({ id: 'safe', name: 'Sejf', stats: { defense: 3 } }),
  item({ id: 'etf', name: 'ETF przyprawowy', kind: 'combined', components: ['spices', 'spices'], stats: { attack: 12 } }),
  item({ id: 'skrytka', name: 'Skrytka na oregano', kind: 'combined', components: ['spices', 'safe'], stats: { attack: 12, defense: 7 } }),
]

describe('getUnitItemPreview', () => {
  it('projects the backend last-match auto-combine rule without mutating equipped ids', () => {
    const equipped = ['safe', 'spices', 'spices']

    const preview = getUnitItemPreview(catalog, equipped, 'safe')

    expect(preview).toMatchObject({
      legal: true,
      mode: 'auto-combine',
      replacedItemId: 'spices',
      slotIndex: 2,
      resultingItem: expect.objectContaining({ id: 'skrytka' }),
      nextItemIds: ['safe', 'spices', 'skrytka'],
      statChanges: { attack: 7, defense: 7 },
    })
    expect(equipped).toEqual(['safe', 'spices', 'spices'])
  })

  it('projects a legal append for a combined incoming item', () => {
    const preview = getUnitItemPreview(catalog, ['spices'], 'skrytka')

    expect(preview).toMatchObject({
      legal: true,
      mode: 'equip',
      nextItemIds: ['spices', 'skrytka'],
      resultingItem: expect.objectContaining({ id: 'skrytka' }),
      statChanges: { attack: 12, defense: 7 },
    })
  })

  it('returns an explicit blocked projection when the unit has three items', () => {
    const equipped = ['safe', 'etf', 'skrytka']
    const preview = getUnitItemPreview(catalog, equipped, 'safe')

    expect(preview).toMatchObject({
      legal: false,
      mode: 'blocked',
      nextItemIds: equipped,
      reason: 'Jednostka ma już 3 przedmioty',
      statChanges: {},
    })
    expect(equipped).toEqual(['safe', 'etf', 'skrytka'])
  })
})
