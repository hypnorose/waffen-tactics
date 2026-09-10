import { describe, expect, it } from 'vitest'
import {
  getTraitThresholdDescription,
  MISSING_TRAIT_DESCRIPTION,
} from '../traits'

describe('getTraitThresholdDescription', () => {
  it('uses the canonical resolved description from the API', () => {
    expect(
      getTraitThresholdDescription(
        { threshold_descriptions: ['+25 ataku'] },
        0,
      ),
    ).toBe('+25 ataku')
  })

  it.each([
    { threshold_descriptions: [] },
    { threshold_descriptions: [''] },
    { threshold_descriptions: ['<rewards.value> ataku'] },
  ])('returns an explicit fallback for an incomplete description', (trait) => {
    expect(getTraitThresholdDescription(trait, 0)).toBe(MISSING_TRAIT_DESCRIPTION)
  })
})
