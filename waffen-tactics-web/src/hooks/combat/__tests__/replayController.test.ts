import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { reconstructCombatState, validateReplayIndex } from '../replayController'
import type { CombatEvent } from '../../types'

const unit = (id: string) => ({
  id,
  name: id,
  hp: 100,
  max_hp: 100,
  attack: 10,
  defense: 5,
  attack_speed: 1,
  star_level: 1,
  position: 'front' as const,
  current_mana: 0,
  max_mana: 50,
  effects: [],
})

const events: CombatEvent[] = [
  {
    type: 'units_init',
    seq: 0,
    timestamp: 0,
    player_units: [unit('player-1')],
    opponent_units: [unit('opponent-1')],
  },
  {
    type: 'animation_start',
    seq: 1,
    timestamp: 0.5,
    attacker_id: 'player-1',
    target_id: 'opponent-1',
  },
  {
    type: 'mana_update',
    seq: 2,
    timestamp: 1,
    unit_id: 'player-1',
    current_mana: 25,
    max_mana: 50,
  },
  {
    type: 'mana_update',
    seq: 3,
    timestamp: 2,
    unit_id: 'player-1',
    current_mana: 50,
    max_mana: 50,
  },
]

describe('replayController', () => {
  beforeEach(() => {
    vi.spyOn(console, 'log').mockImplementation(() => undefined)
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
  })

  afterEach(() => vi.restoreAllMocks())

  it('reconstructs the same state after forward and backward seeks', () => {
    const atFirstMana = reconstructCombatState(events, 2)
    const atEnd = reconstructCombatState(events, 3)
    const returnedToFirstMana = reconstructCombatState(events, 2)

    expect(atFirstMana.playerUnits[0].current_mana).toBe(25)
    expect(atEnd.playerUnits[0].current_mana).toBe(50)
    expect(returnedToFirstMana).toEqual(atFirstMana)
    expect(returnedToFirstMana.activeAnimations).toEqual([])
  })

  it('restarts from the canonical first event without reusing terminal state', () => {
    const terminal = reconstructCombatState(events, 3)
    const restarted = reconstructCombatState(events, 0)

    expect(terminal.playerUnits[0].current_mana).toBe(50)
    expect(restarted.playerUnits[0].current_mana).toBe(0)
    expect(restarted.playerUnits).toHaveLength(1)
  })

  it('rejects unavailable seek positions instead of inventing state', () => {
    expect(() => validateReplayIndex(events, 4)).toThrow('Pozycja replayu 4 jest poza zakresem')
    expect(() => reconstructCombatState(events, 4)).toThrow('Pozycja replayu 4 jest poza zakresem')
    expect(() => validateReplayIndex(events, 1.5)).toThrow('musi być liczbą całkowitą')
  })
})
