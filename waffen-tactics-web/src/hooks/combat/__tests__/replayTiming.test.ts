import { describe, expect, it } from 'vitest'
import { COMBAT_SPEED_PRESETS, normalizeCombatSpeed } from '../replayTiming'

describe('replay timing speed contract', () => {
  it('keeps only the approved replay speed presets', () => {
    expect(COMBAT_SPEED_PRESETS).toEqual([1, 2, 5])
    expect(normalizeCombatSpeed('2')).toBe(2)
    expect(normalizeCombatSpeed(5)).toBe(5)
    expect(normalizeCombatSpeed('1.5')).toBe(1)
    expect(normalizeCombatSpeed('not-a-speed')).toBe(1)
  })
})
