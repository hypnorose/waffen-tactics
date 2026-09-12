import { describe, expect, it } from 'vitest'
import { createEmptyCombatState } from '../replayController'
import { processReplayEvent } from '../replayEventProcessor'
import type { CombatEvent, CombatState } from '../../types'

const unit = (id: string, hp = 100) => ({
  id,
  name: id,
  hp,
  max_hp: 100,
  attack: 10,
  defense: 5,
  attack_speed: 1,
  star_level: 1,
  position: 'front' as const,
  current_mana: 0,
  max_mana: 50,
  shield: 0,
  effects: [],
})

const stateWithUnits = (): CombatState => ({
  ...createEmptyCombatState(),
  playerUnits: [unit('player-1')],
  opponentUnits: [unit('opponent-1')],
})

describe('replayEventProcessor', () => {
  it('returns canonical state changes and gold metadata without React dependencies', () => {
    const result = processReplayEvent({
      currentState: stateWithUnits(),
      event: {
        type: 'gold_income',
        seq: 4,
        base: 2,
        interest: 1,
        milestone: 3,
        win_bonus: 1,
        total: 7,
        item_parts: ['item_part'],
      },
      pendingEvents: [],
    })

    expect(result.state).toBeDefined()
    expect(result.state?.playerUnits).toEqual(stateWithUnits().playerUnits)
    expect(result.goldBreakdown).toEqual({
      base: 2,
      interest: 1,
      milestone: 3,
      win_bonus: 1,
      total: 7,
      item_parts: ['item_part'],
    })
    expect(result.shouldStop).toBe(false)
  })

  it('turns replay validation failures into a diagnostic and stop decision', () => {
    const pending: CombatEvent[] = [{ type: 'end', seq: 3 }]
    const result = processReplayEvent({
      currentState: stateWithUnits(),
      event: { type: 'mana_update', seq: 2, unit_id: 'missing', current_mana: 10 },
      pendingEvents: pending,
    })

    expect(result.state).toBeUndefined()
    expect(result.shouldStop).toBe(true)
    expect(result.validationError?.unitId).toBe('missing')
    expect(result.desyncs[0]).toMatchObject({
      unit_id: 'missing',
      seq: 2,
      pending_events: pending,
    })
    expect(result.desyncs[0].note).toContain('replay validation failed')
  })

  it('reports malformed server snapshots instead of throwing from the replay loop', () => {
    const result = processReplayEvent({
      currentState: stateWithUnits(),
      event: {
        type: 'mana_update',
        seq: 2,
        unit_id: 'player-1',
        current_mana: 10,
        game_state: {} as CombatEvent['game_state'],
      },
      pendingEvents: [{ type: 'end', seq: 3 }],
    })

    expect(result.state?.playerUnits[0].current_mana).toBe(10)
    expect(result.shouldStop).toBe(true)
    expect(result.desyncs).toHaveLength(1)
    expect(result.desyncs[0].diff.snapshot).toEqual({ ui: 'not_compared', server: expect.any(String) })
    expect(result.desyncs[0].note).toContain('combat snapshot validation failed')
  })
})
