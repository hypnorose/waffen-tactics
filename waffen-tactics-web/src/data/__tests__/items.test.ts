import { describe, expect, it } from 'vitest'
import { getItemMechanicDescription, getUnitItemPreview, type Item } from '../items'

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

describe('getItemMechanicDescription', () => {
  it('removes a stat-only description because the stat row is generated from stats', () => {
    const itemDefinition = item({
      stats: { attack: 30 },
      description: '+30 ataku.',
    })

    expect(getItemMechanicDescription(itemDefinition)).toBeUndefined()
  })

  it('keeps a unique mechanic after removing several generated stat clauses', () => {
    const itemDefinition = item({
      stats: { attack: 10, mana_regen: 3 },
      description: '+10 ataku, +3 regeneracji many, +5 many przy ataku.',
    })

    expect(getItemMechanicDescription(itemDefinition)).toBe('+5 many przy ataku.')
  })

  it('supports decimal formatting and does not remove different proc values', () => {
    const itemDefinition = item({
      stats: { defense: 15, attack_speed: 0.15 },
      description: '+15 obrony, +0,15 szybkości ataku. Przy ataku właściciel zyskuje +1 ataku, +0,10 szybkości ataku i +1 obrony; maksymalnie 10 stacków.',
    })

    expect(getItemMechanicDescription(itemDefinition)).toContain('Przy ataku właściciel zyskuje +1 ataku')
    expect(getItemMechanicDescription(itemDefinition)).toContain('+0,10 szybkości ataku')
  })

  it('removes a declarative duplicate even when the description starts with a filler verb', () => {
    const itemDefinition = item({
      stats: { attack: 10 },
      description: 'Daje +10 ATK.',
    })

    expect(getItemMechanicDescription(itemDefinition)).toBeUndefined()
  })
})
