import { describe, expect, it } from 'vitest'
import { compareUnits } from '../desync'
import { CombatEvent, Unit } from '../types'

const event: CombatEvent = { type: 'passive_triggered', seq: 8, timestamp: 0 }

function makeUnit(overrides: Partial<Unit> = {}): Unit {
  return {
    id: 'buba',
    name: 'Buba',
    hp: 600,
    max_hp: 600,
    attack: 62,
    defense: 24,
    star_level: 1,
    position: 'front',
    effects: [{ id: 'attack-buff', type: 'buff', stat: 'attack', value: 5, duration: undefined }],
    current_mana: 0,
    max_mana: 100,
    buffed_stats: { hp: 600, attack: 62, defense: 24, attack_speed: 1, max_mana: 100 },
    ...overrides,
  }
}

describe('combat desync comparison', () => {
  it('ignores hidden passive mechanics such as lifesteal', () => {
    const uiUnit = makeUnit()
    const serverUnit = {
      ...makeUnit(),
      attack_speed: 1,
      shield: 0,
      effects: [
        ...(uiUnit.effects || []),
        { id: 'passive-lifesteal', type: 'lifesteal', value: 8 },
      ],
    }

    expect(compareUnits([uiUnit], [serverUnit], 'player', event)).toEqual([])
  })

  it('still reports authoritative stat differences', () => {
    const uiUnit = makeUnit()
    const serverUnit = makeUnit({ attack: 67 })

    const desyncs = compareUnits([uiUnit], [serverUnit], 'player', event)

    expect(desyncs).toHaveLength(1)
    expect(desyncs[0].diff.attack).toEqual({ ui: 62, server: 67 })
  })
})
