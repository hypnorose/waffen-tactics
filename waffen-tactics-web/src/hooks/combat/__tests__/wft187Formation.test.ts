import { describe, expect, it } from 'vitest'
import { applyCombatEvent } from '../applyEvent'
import { reconstructCombatState } from '../replayController'
import type { CombatEvent, CombatState, Unit } from '../types'

function unit(id: string, position: 'front' | 'back' = 'front'): Unit {
  return {
    id,
    name: id,
    hp: 100,
    max_hp: 100,
    attack: 10,
    defense: 5,
    attack_speed: 1,
    star_level: 1,
    position,
    effects: [],
  }
}

function state(): CombatState {
  return {
    playerUnits: [unit('e7e66be4', 'back')],
    opponentUnits: [unit('opp_1')],
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
}

const formationEvent: CombatEvent = {
  type: 'formation_changed',
  seq: 233,
  event_id: 'combat:233',
  unit_id: 'opp_1',
  previous_position: 'front',
  new_position: 'back',
  position: 'back',
  source_id: 'e7e66be4',
  passive_id: 'set2.passive.yossarian',
  trigger: 'on_bonus_attack',
  effect: 'swap_enemy_line',
  cause: 'swap_enemy_line',
}

describe('WFT-187 formation_changed replay contract', () => {
  it('applies the explicit destination before the following attack', () => {
    const next = applyCombatEvent(state(), formationEvent, { simTime: 3.75 })

    expect(next.opponentUnits[0].position).toBe('back')
  })

  it('is idempotent when a reconnect re-delivers the same event', () => {
    const next = applyCombatEvent(state(), formationEvent, { simTime: 3.75 })
    const duplicate = applyCombatEvent(next, formationEvent, { simTime: 3.75 })

    expect(duplicate.opponentUnits[0].position).toBe('back')
  })

  it('rebuilds the same position from the canonical history on seek', () => {
    const replayed = reconstructCombatState([formationEvent], 0, state())

    expect(replayed.opponentUnits[0].position).toBe('back')
  })

  it('rejects an unknown current position without mutating the state', () => {
    const snapshot = state()
    snapshot.opponentUnits = snapshot.opponentUnits.map(unit => ({ ...unit, position: undefined }))

    expect(() => applyCombatEvent(snapshot, formationEvent, { simTime: 3.75 })).toThrow(
      '[REPLAY_VALIDATION] formation_changed event seq=233 position mismatch: expected current=front, actual=undefined'
    )
    expect(snapshot.opponentUnits[0].position).toBeUndefined()
  })

  it('rejects a different out-of-order transition even when its destination is current', () => {
    const outOfOrder: CombatEvent = {
      ...formationEvent,
      event_id: 'combat:out-of-order',
      previous_position: 'back',
      new_position: 'front',
    }

    expect(() => applyCombatEvent(state(), outOfOrder, { simTime: 3.75 })).toThrow(
      '[REPLAY_VALIDATION] formation_changed event seq=233 position mismatch: expected current=back, actual=front'
    )
  })

  it('rejects a formation event without transport identity', () => {
    const missingIdentity = { ...formationEvent, event_id: undefined }

    expect(() => applyCombatEvent(state(), missingIdentity, { simTime: 3.75 })).toThrow(
      '[REPLAY_VALIDATION] formation_changed event seq=233 missing required event_id'
    )
  })
})
