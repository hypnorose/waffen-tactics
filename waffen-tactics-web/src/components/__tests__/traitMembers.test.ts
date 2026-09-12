import { describe, expect, it } from 'vitest'
import { getUnitsForTrait } from '../traitMembers'

describe('getUnitsForTrait', () => {
  it('uses canonical unit.traits instead of legacy factions/classes metadata', () => {
    const units = [
      {
        id: 'canonical-member',
        traits: ['Konfident'],
        factions: [],
        classes: [],
      },
      {
        id: 'legacy-only-member',
        traits: [],
        factions: ['Konfident'],
        classes: [],
      },
    ]

    expect(getUnitsForTrait(units, 'Konfident').map(unit => unit.id)).toEqual(['canonical-member'])
  })

  it('fails closed for malformed membership and blank trait names', () => {
    const units = [
      { id: 'malformed', traits: 'Konfident' },
      { id: 'wrong-trait', traits: ['Szachista'] },
    ]

    expect(getUnitsForTrait(units, 'Konfident')).toEqual([])
    expect(getUnitsForTrait(units, '   ')).toEqual([])
  })
})
