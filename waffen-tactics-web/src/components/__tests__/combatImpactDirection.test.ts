import { describe, expect, it } from 'vitest'
import { getCombatImpactDirection } from '../combatImpactDirection'

const fallback = 'from-bottom' as const

describe('combat impact direction', () => {
  it.each([
    [{ x: 100, y: 20 }, { x: 100, y: 120 }, 'from-top'],
    [{ x: 100, y: 120 }, { x: 100, y: 20 }, 'from-bottom'],
    [{ x: 20, y: 100 }, { x: 120, y: 100 }, 'from-left'],
    [{ x: 120, y: 100 }, { x: 20, y: 100 }, 'from-right'],
  ] as const)('maps source-to-target geometry to %s', (source, target, expected) => {
    expect(getCombatImpactDirection(source, target, fallback)).toBe(expected)
  })

  it('uses the stable side fallback when an anchor is unavailable', () => {
    expect(getCombatImpactDirection(null, { x: 10, y: 10 }, fallback)).toBe(fallback)
    expect(getCombatImpactDirection({ x: 10, y: 10 }, { x: 10, y: 10 }, fallback)).toBe(fallback)
  })
})
