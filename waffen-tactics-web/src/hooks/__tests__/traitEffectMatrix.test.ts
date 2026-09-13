import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { getCanonicalTraitDescription, getTraitDescription, getTraitEffectPresentation } from '../combatOverlayUtils'

type CanonicalTrait = {
  name: string
  thresholds: number[]
  threshold_descriptions: string[]
  modular_effects: Array<Array<Record<string, any>>>
}

const canonicalTraits = JSON.parse(
  readFileSync(resolve(process.cwd(), '..', 'waffen-tactics', 'traits.json'), 'utf-8'),
).traits as CanonicalTrait[]

describe('WFT-217 canonical trait presentation matrix', () => {
  it('presents every tier and all 32 canonical effects without review fallbacks', () => {
    let effectCount = 0

    for (const trait of canonicalTraits) {
      expect(trait.thresholds).toHaveLength(trait.modular_effects.length)
      expect(trait.threshold_descriptions).toHaveLength(trait.thresholds.length)

      for (const [tierIndex, tierEffects] of trait.modular_effects.entries()) {
        const tier = tierIndex + 1
        const presentation = getTraitEffectPresentation(trait, tier)
        effectCount += tierEffects.length

        expect(presentation).toHaveLength(tierEffects.length)
        expect(getCanonicalTraitDescription(trait, tier)).toBeTruthy()
        expect(getTraitDescription(trait, tier)).not.toContain('Do review')
        expect(getTraitDescription(trait, tier)).not.toMatch(/\d[.,]?\d*\/\d/)

        for (const effect of presentation) {
          expect(effect.trigger).not.toContain('Do review')
          expect(effect.target).not.toContain('Do review')
          expect(effect.values.length).toBeGreaterThan(0)
          expect(effect.lifecycle).not.toContain('Do review')
          expect(effect.activation).not.toContain('Do review')
          expect(effect.duration).not.toContain('Do review')
          expect(effect.refresh).not.toContain('Do review')
          expect(effect.retrigger).not.toContain('Do review')
          expect(effect.stacking).not.toContain('Do review')
          expect(effect.expiresWhen).not.toContain('Do review')
        }
      }
    }

    expect(canonicalTraits).toHaveLength(12)
    expect(effectCount).toBe(32)
  })
})
