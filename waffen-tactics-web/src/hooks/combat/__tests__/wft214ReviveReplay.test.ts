import { describe, expect, it, vi } from 'vitest'
import fixture from '../../../../test-fixtures/wft214_revive_replay.json'
import { applyCombatEvent, CombatReplayValidationError } from '../applyEvent'
import { createEmptyCombatState, reconstructCombatState } from '../replayController'
import { processReplayEvent } from '../replayEventProcessor'
import type { CombatEvent, CombatState, Unit } from '../types'

const events = fixture as CombatEvent[]

function stateWithFixtureUnits(): CombatState {
  const initial = events[0]
  return applyCombatEvent(createEmptyCombatState(), initial, { simTime: 0 })
}

function unit(state: CombatState, id: string): Unit {
  return [...state.playerUnits, ...state.opponentUnits].find(candidate => candidate.id === id)!
}

function replayUntil(seq: number): CombatState {
  const index = events.findIndex(event => event.seq === seq)
  if (index < 0) throw new Error(`Missing fixture seq=${seq}`)
  return reconstructCombatState(events, index)
}

describe('WFT-214 canonical revive replay matrix', () => {
  it('replays seq 1103 -> 1104 and expires protection without changing canonical HP', () => {
    const afterDeath = replayUntil(1103)
    expect(unit(afterDeath, 'opp_0').hp).toBe(0)

    const beforeExpiry = replayUntil(1105)
    expect(unit(beforeExpiry, 'opp_0').hp).toBe(480)
    expect(unit(beforeExpiry, 'opp_0').effects).toContainEqual(expect.objectContaining({
      id: 'set2:opp_0:revive-untargetable',
      type: 'untargetable',
      duration: 0.75,
      expires_at: 8.2,
      expiresAt: 8.2,
    }))

    const afterExpiry = replayUntil(1106)
    expect(unit(afterExpiry, 'opp_0').hp).toBe(480)
    expect(unit(afterExpiry, 'opp_0').effects).toEqual([])
  })

  it.each([
    ['player_0', 1203, 1204, 1206],
    ['opp_0', 1103, 1104, 1106],
  ] as const)('applies the same lifecycle for %s', (unitId, deathSeq, reviveSeq, expirySeq) => {
    const afterDeath = replayUntil(deathSeq)
    expect(unit(afterDeath, unitId).hp).toBe(0)

    const afterRevive = replayUntil(reviveSeq)
    expect(unit(afterRevive, unitId).hp).toBe(480)
    expect(unit(afterRevive, unitId).effects).toHaveLength(1)

    const afterExpiry = replayUntil(expirySeq)
    expect(unit(afterExpiry, unitId).hp).toBe(480)
    expect(unit(afterExpiry, unitId).effects).toEqual([])
  })

  it('is deterministic after reconnect duplicate delivery and full replay seek', () => {
    const initial = stateWithFixtureUnits()
    const died = applyCombatEvent(initial, events[1], { simTime: 7.45 })
    const revived = applyCombatEvent(died, events[2], { simTime: 7.45 })
    const duplicate = applyCombatEvent(revived, events[2], { simTime: 7.45 })

    expect(duplicate).toBe(revived)
    expect(reconstructCombatState(events, events.length - 1)).toEqual(
      reconstructCombatState(events, events.length - 1),
    )
    expect(unit(revived, 'opp_0').hp).toBe(480)
    expect(unit(revived, 'opp_0').effects).toHaveLength(1)
  })

  it.each(['unit_heal', 'heal', 'hp_regen', 'regen_gain'] as const)(
    'ignores ordinary post-death %s without restoring HP',
    eventType => {
      const state = replayUntil(1103)
      const event: CombatEvent = {
        type: eventType,
        unit_id: 'opp_0',
        unit_name: 'Nicość',
        cause: 'healing_aura',
        post_hp: 480,
        amount: 10,
        post_hp_regen_per_sec: eventType === 'regen_gain' ? 5 : undefined,
        seq: 1110,
      }

      const next = applyCombatEvent(state, event, { simTime: state.simTime })
      expect(unit(next, 'opp_0').hp).toBe(0)
      expect(unit(next, 'opp_0').effects).toEqual([])
    },
  )

  it('fails closed through replay processing when a revive field is missing', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const state = replayUntil(1103)
    const malformed = { ...events[2] }
    delete malformed.effect_id

    const result = processReplayEvent({
      currentState: state,
      event: malformed,
      pendingEvents: events.slice(3, 4),
    })

    expect(result.shouldStop).toBe(true)
    expect(result.state).toBeUndefined()
    expect(result.validationError).toBeInstanceOf(CombatReplayValidationError)
    expect(result.desyncs[0].note).toContain('replay validation failed')
    expect(unit(state, 'opp_0').hp).toBe(0)
  })
})
