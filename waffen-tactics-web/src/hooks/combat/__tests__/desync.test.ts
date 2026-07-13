import { describe, expect, it } from 'vitest'
import { applyCombatEvent } from '../applyEvent'
import { compareCombatStates, compareUnits, shouldCompareCombatSnapshot } from '../desync'
import { CombatEvent, CombatState, Unit } from '../types'

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

  it('does not compare snapshots attached to explanatory passive events', () => {
    const passiveEvent: CombatEvent = { type: 'passive_triggered', seq: 88, timestamp: 2.85 }
    const state: CombatState = {
      playerUnits: [makeUnit()],
      opponentUnits: [],
      combatLog: [],
      isFinished: false,
      victory: null,
      finalState: null,
      synergies: {},
      traits: [],
      opponentInfo: null,
      regenMap: {},
      simTime: 2.85,
    }
    const snapshot = {
      player_units: [{ ...makeUnit(), hp: 500 }],
      opponent_units: [],
    }

    expect(shouldCompareCombatSnapshot(passiveEvent)).toBe(false)
    expect(compareCombatStates(state, snapshot, passiveEvent)).toEqual([])
  })

  it('keeps Hyodo max HP and current HP synchronized after the canonical event', () => {
    const state: CombatState = {
      playerUnits: [makeUnit({ id: '9d4c477e', name: 'Hyodo888', hp: 720, max_hp: 720, buffed_stats: { hp: 720, attack: 36, defense: 36, attack_speed: 0.8, max_mana: 50 } })],
      opponentUnits: [],
      combatLog: [],
      isFinished: false,
      victory: null,
      finalState: null,
      synergies: {},
      traits: [],
      opponentInfo: null,
      regenMap: {},
      simTime: 0,
    }
    const statEvent: CombatEvent = {
      type: 'stat_buff',
      unit_id: '9d4c477e',
      unit_name: 'Hyodo888',
      stat: 'max_hp',
      amount: 10,
      value: 10,
      value_type: 'percentage',
      permanent: true,
      duration: null,
      effect_id: 'hyodo-max-hp',
      applied_delta: 72,
      pre_hp: 720,
      post_hp: 792,
      seq: 4,
      timestamp: 0,
    }
    const replayed = applyCombatEvent(state, statEvent, { simTime: 0 })
    const serverState = {
      player_units: [{ ...replayed.playerUnits[0], attack_speed: 0.8, shield: 0, effects: replayed.playerUnits[0].effects }],
      opponent_units: [],
    }

    expect(replayed.playerUnits[0].hp).toBe(792)
    expect(replayed.playerUnits[0].max_hp).toBe(792)
    expect(compareCombatStates(replayed, serverState, statEvent)).toEqual([])
  })
})
