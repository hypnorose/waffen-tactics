import { describe, expect, it } from 'vitest'
import {
  CombatSnapshotValidationError,
  validateCombatEventSnapshot,
  validateCombatSnapshot,
} from '../snapshotContract'

function unit(id: string) {
  return {
    id,
    hp: 100,
    max_hp: 100,
    current_mana: 20,
    max_mana: 100,
    shield: 0,
    effects: [{ id: `effect:${id}`, type: 'buff' }],
    buffed_stats: { hp: 100 },
    item_runtime_state: {},
    passive: null,
  }
}

function snapshot() {
  return {
    player_units: [unit('player-1')],
    opponent_units: [unit('opponent-1')],
  }
}

describe('combat snapshot contract', () => {
  it('accepts a structured event snapshot', () => {
    expect(() => validateCombatEventSnapshot({
      type: 'unit_attack',
      seq: 12,
      game_state: snapshot(),
    })).not.toThrow()
  })

  it('rejects stringified units and reports the event sequence', () => {
    const invalid = snapshot()
    invalid.player_units = '@{id=player-1}' as unknown as typeof invalid.player_units

    expect(() => validateCombatEventSnapshot({
      type: 'state_snapshot',
      seq: 90,
      player_units: invalid.player_units,
      opponent_units: invalid.opponent_units,
    })).toThrowError(/state_snapshot seq=90.*player_units/)
  })

  it('rejects stringified effects instead of silently comparing characters', () => {
    const invalid = snapshot()
    invalid.player_units[0].effects = ['System.Object[]'] as any

    expect(() => validateCombatSnapshot(invalid, 'state_snapshot seq=91'))
      .toThrowError(CombatSnapshotValidationError)
  })
})
