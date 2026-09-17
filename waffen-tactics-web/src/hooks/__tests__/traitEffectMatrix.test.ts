import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { getCanonicalTraitDescription, getTraitDescription } from '../combatOverlayUtils'

type CanonicalTrait = {
  name: string
  thresholds: number[]
  threshold_descriptions: string[]
  modular_effects: Array<Array<Record<string, any>>>
}

const canonicalTraits = JSON.parse(
  readFileSync(resolve(process.cwd(), '..', 'waffen-tactics', 'traits.json'), 'utf-8'),
).traits as CanonicalTrait[]

describe('WFT-217 canonical trait description matrix', () => {
  it('presents a resolved, non-templated description for every tier of every trait', () => {
    for (const trait of canonicalTraits) {
      expect(trait.thresholds).toHaveLength(trait.modular_effects.length)
      expect(trait.threshold_descriptions).toHaveLength(trait.thresholds.length)

      for (const tierIndex of trait.modular_effects.keys()) {
        const tier = tierIndex + 1

        expect(getCanonicalTraitDescription(trait, tier)).toBeTruthy()
        expect(getTraitDescription(trait, tier)).not.toContain('Do review')
        expect(getTraitDescription(trait, tier)).not.toMatch(/\d[.,]?\d*\/\d/)
      }
    }

    expect(canonicalTraits).toHaveLength(12)
  })
})
