/**
 * Frontend Combat Event Handler Tests
 *
 * Tests the applyEvent function using real combat event dumps from the backend.
 * These tests validate that the frontend correctly reconstructs combat state
 * from event streams, catching bugs like:
 * - Missing effect IDs
 * - Wrong effect types (buff vs debuff)
 * - Effect duplication
 * - Shallow copy mutations
 * - State desyncs
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { applyCombatEvent, CombatReplayValidationError } from '../applyEvent'
import { compareCombatStates } from '../desync'
import { CombatState, CombatEvent } from '../types'

// Helper to create initial combat state
function createInitialState(): CombatState {
  return {
    playerUnits: [],
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
    defeatMessage: undefined
  }
}

// Helper to create a test unit
function createTestUnit(id: string, name: string, hp: number, attack: number, defense: number) {
  return {
    id,
    name,
    hp,
    max_hp: hp,
    attack,
    defense,
    attack_speed: 1.0,
    star_level: 1,
    position: 'front' as const,
    effects: [],
    current_mana: 0,
    max_mana: 100,
    shield: 0,
    base_stats: { hp, attack, defense, attack_speed: 1.0, max_mana: 100 },
    buffed_stats: { hp, attack, defense, attack_speed: 1.0, max_mana: 100, hp_regen_per_sec: 0 }
  }
}

describe('applyCombatEvent - Effect Handling', () => {
  let state: CombatState
  const invalidEffectIds: unknown[] = [undefined, '', '   ', 123]

  beforeEach(() => {
    state = createInitialState()
    state.playerUnits = [
      createTestUnit('player_0', 'TestPlayer', 500, 50, 25)
    ]
    state.opponentUnits = [
      createTestUnit('opp_0', 'TestOpponent', 600, 60, 30)
    ]
  })

  describe('units_init canonical formation', () => {
    it('rejects a player unit without a canonical position without mutating the roster', () => {
      const event: CombatEvent = {
        type: 'units_init',
        player_units: [{ ...state.playerUnits[0], position: undefined }],
        opponent_units: state.opponentUnits,
        seq: 1,
      }

      const next = applyCombatEvent(state, event, { simTime: 0 })

      expect(next.playerUnits).toEqual(state.playerUnits)
      expect(next.opponentUnits).toEqual(state.opponentUnits)
    })

    it('rejects an opponent unit with an invalid canonical position without mutating the roster', () => {
      const event: CombatEvent = {
        type: 'units_init',
        player_units: state.playerUnits,
        opponent_units: [{ ...state.opponentUnits[0], position: 'middle' }],
        seq: 2,
      }

      const next = applyCombatEvent(state, event, { simTime: 0 })

      expect(next.playerUnits).toEqual(state.playerUnits)
      expect(next.opponentUnits).toEqual(state.opponentUnits)
    })
  })

  it('rejects HP alias fallbacks and leaves reducer state unchanged', () => {
    const cases: CombatEvent[] = [
      { type: 'attack', target_id: 'opp_0', post_hp: 1, seq: 1 },
      { type: 'unit_heal', unit_id: 'player_0', unit_hp: 999, seq: 2 },
      { type: 'damage_over_time_tick', unit_id: 'player_0', effect_id: 'dot-1', unit_hp: 1, seq: 3 },
      { type: 'hp_regen', unit_id: 'player_0', unit_hp: 999, seq: 4 },
      { type: 'damage_over_time_expired', unit_id: 'player_0', effect_id: 'dot-1', unit_hp: 999, seq: 5 }
    ]

    for (const event of cases) {
      const next = applyCombatEvent(state, event, { simTime: 1.0 })
      expect(next.playerUnits[0].hp).toBe(500)
      expect(next.opponentUnits[0].hp).toBe(600)
    }
  })

  it('replays damage_dodged without changing HP and deduplicates reconnect delivery', () => {
    const event: CombatEvent = {
      type: 'damage_dodged',
      attacker_id: 'player_0',
      attacker_name: 'TestPlayer',
      unit_id: 'opp_0',
      unit_name: 'TestOpponent',
      target_id: 'opp_0',
      target_name: 'TestOpponent',
      damage: 0,
      applied_damage: 0,
      shield_absorbed: 0,
      post_hp: 600,
      target_hp: 600,
      post_shield: 0,
      seq: 84,
      event_id: 'combat:84',
      timestamp: 8.4,
    }

    const next = applyCombatEvent(state, event, { simTime: 0 })
    const duplicate = applyCombatEvent(next, event, { simTime: 8.4 })

    expect(next.opponentUnits[0].hp).toBe(600)
    expect(next.opponentUnits[0].shield).toBe(0)
    expect(next.combatLog).toEqual(['[DODGE] TestOpponent unika obrażeń od TestPlayer'])
    expect(duplicate).toBe(next)
  })

  it('rejects damage_dodged with an unknown attacker or non-zero damage', () => {
    expect(() => applyCombatEvent(state, {
      type: 'damage_dodged',
      attacker_id: 'ghost-attacker',
      unit_id: 'opp_0',
      target_id: 'opp_0',
      seq: 84,
    }, { simTime: 0 })).toThrow('[REPLAY_VALIDATION] damage_dodged event seq=84 references unknown unit_id=ghost-attacker')

    expect(() => applyCombatEvent(state, {
      type: 'damage_dodged',
      attacker_id: 'player_0',
      unit_id: 'opp_0',
      target_id: 'opp_0',
      applied_damage: 1,
      seq: 85,
    }, { simTime: 0 })).toThrow('[REPLAY_VALIDATION] damage_dodged event seq=85 must be a zero-damage outcome for applied_damage')
  })

  describe('unit identity validation', () => {
    const unitTargetedTypes = ['unit_died', 'heal', 'unit_heal', 'hp_regen', 'damage_over_time_applied'] as const

    it.each(unitTargetedTypes)('rejects %s when unit_id is missing', (type) => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState
      const event: CombatEvent = {
        type,
        side: 'team_a',
        post_hp: 499,
        effect_id: 'dot-1',
        damage: 10,
        expires_at: 4,
        seq: 20,
      }

      expect(() => applyCombatEvent(state, event, { simTime: 1.0 }))
        .toThrow(`[REPLAY_VALIDATION] ${type} event seq=20 missing required unit_id`)
      expect(state).toEqual(original)
    })

    it.each(unitTargetedTypes)('rejects %s when unit_id is unknown', (type) => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState
      const event: CombatEvent = {
        type,
        unit_id: 'ghost-unit',
        side: 'team_a',
        post_hp: 499,
        effect_id: 'dot-1',
        damage: 10,
        expires_at: 4,
        seq: 21,
      }

      expect(() => applyCombatEvent(state, event, { simTime: 1.0 }))
        .toThrow(`[REPLAY_VALIDATION] ${type} event seq=21 references unknown unit_id=ghost-unit`)
      expect(state).toEqual(original)
    })

    const remainingRequiredUnitTypes: Array<{ type: string, payload?: Partial<CombatEvent> }> = [
      { type: 'stat_buff', payload: { applied_delta: 1 } },
      { type: 'mana_update', payload: { current_mana: 1 } },
      { type: 'regen_gain', payload: { amount_per_sec: 1, total_amount: 1 } },
      { type: 'shield_applied', payload: { effect_id: 'shield-1', amount: 10, post_shield: 10 } },
      { type: 'effect_applied', payload: { effect_id: 'effect-1', effect: { id: 'effect-1', type: 'stun' } } },
      { type: 'shield_broken' },
      { type: 'unit_stunned' },
      { type: 'damage_over_time_tick', payload: { post_hp: 499 } },
      { type: 'damage_over_time_expired', payload: { effect_id: 'dot-1', post_hp: 499 } },
      { type: 'effect_expired', payload: { effect_id: 'effect-1' } },
    ]

    it.each(remainingRequiredUnitTypes)('rejects $type when unit_id is missing', ({ type, payload }) => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState
      const event: CombatEvent = { type, ...payload, seq: 22 }

      expect(() => applyCombatEvent(state, event, { simTime: 1.0 }))
        .toThrow(`[REPLAY_VALIDATION] ${type} event seq=22 missing required unit_id`)
      expect(state).toEqual(original)
    })

    it.each(remainingRequiredUnitTypes)('rejects $type when unit_id is unknown', ({ type, payload }) => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState
      const event: CombatEvent = { type, unit_id: 'ghost-unit', ...payload, seq: 23 }

      expect(() => applyCombatEvent(state, event, { simTime: 1.0 }))
        .toThrow(`[REPLAY_VALIDATION] ${type} event seq=23 references unknown unit_id=ghost-unit`)
      expect(state).toEqual(original)
    })

    it('rejects an unknown attack target before applying a unit_attack attacker update', () => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState
      const event: CombatEvent = {
        type: 'unit_attack',
        attacker_id: 'player_0',
        attacker_current_mana: 77,
        target_id: 'ghost-target',
        target_hp: 1,
        seq: 24,
      }

      expect(() => applyCombatEvent(state, event, { simTime: 1.0 }))
        .toThrow('[REPLAY_VALIDATION] unit_attack event seq=24 references unknown unit_id=ghost-target')
      expect(state).toEqual(original)
    })

    it('rejects an unknown supplied unit_attack attacker', () => {
      const event: CombatEvent = {
        type: 'unit_attack',
        attacker_id: 'ghost-attacker',
        target_id: 'opp_0',
        target_hp: 599,
        seq: 25,
      }

      expect(() => applyCombatEvent(state, event, { simTime: 1.0 }))
        .toThrow('[REPLAY_VALIDATION] unit_attack event seq=25 references unknown unit_id=ghost-attacker')
    })

    it('rejects an unknown attack target while preserving valid no-target compatibility', () => {
      expect(() => applyCombatEvent(state, {
        type: 'attack',
        target_id: 'ghost-target',
        target_hp: 1,
        seq: 26,
      }, { simTime: 1.0 })).toThrow(
        '[REPLAY_VALIDATION] attack event seq=26 references unknown unit_id=ghost-target'
      )

      expect(() => applyCombatEvent(state, {
        type: 'attack',
        attacker_id: 'player_0',
        seq: 27,
      }, { simTime: 1.0 })).not.toThrow()
    })
  })

  describe('event type validation', () => {
    it('rejects unsupported replay event types with typed sequence context', () => {
      const event: CombatEvent = { type: 'future_event', seq: 28 }

      expect(() => applyCombatEvent(state, event, { simTime: 1.0 }))
        .toThrowError(CombatReplayValidationError)
      expect(() => applyCombatEvent(state, event, { simTime: 1.0 }))
        .toThrow('[REPLAY_VALIDATION] future_event event seq=28 unsupported event type=future_event')
      expect(state.playerUnits[0].hp).toBe(500)
      expect(state.opponentUnits[0].hp).toBe(600)
    })

    it.each(['gold_income', 'skill_cast', 'passive_triggered'] as const)
      ('keeps %s as an explicit metadata compatibility no-op', (type) => {
        const next = applyCombatEvent(state, { type, seq: 29 }, { simTime: 1.0 })

        expect(next.playerUnits).toEqual(state.playerUnits)
        expect(next.opponentUnits).toEqual(state.opponentUnits)
      })
  })

  it('uses canonical post_shield for damage instead of subtracting shield_absorbed', () => {
    const shieldedState = {
      ...state,
      opponentUnits: state.opponentUnits.map(unit => ({ ...unit, shield: 25 }))
    }
    const next = applyCombatEvent(shieldedState, {
      type: 'unit_attack',
      attacker_id: 'player_0',
      target_id: 'opp_0',
      target_hp: 580,
      shield_absorbed: 20,
      post_shield: 3,
      seq: 6,
    }, { simTime: 1.0 })

    expect(next.opponentUnits[0].hp).toBe(580)
    expect(next.opponentUnits[0].shield).toBe(3)
  })

  it('rejects shield-absorbing damage without canonical post_shield', () => {
    const shieldedState = {
      ...state,
      opponentUnits: state.opponentUnits.map(unit => ({ ...unit, shield: 25 }))
    }
    const next = applyCombatEvent(shieldedState, {
      type: 'unit_attack',
      attacker_id: 'player_0',
      target_id: 'opp_0',
      target_hp: 580,
      shield_absorbed: 20,
      seq: 7,
    }, { simTime: 1.0 })

    expect(next.opponentUnits[0].hp).toBe(600)
    expect(next.opponentUnits[0].shield).toBe(25)
  })

  it('applies canonical post_shield for shield-absorbed DoT ticks', () => {
    const shieldedState = {
      ...state,
      playerUnits: state.playerUnits.map(unit => ({ ...unit, shield: 10 }))
    }
    const next = applyCombatEvent(shieldedState, {
      type: 'damage_over_time_tick',
      unit_id: 'player_0',
      effect_id: 'dot-1',
      pre_hp: 500,
      post_hp: 500,
      shield_absorbed: 8,
      post_shield: 2,
      unit_shield: 99,
      seq: 8,
    }, { simTime: 1.0 })

    expect(next.playerUnits[0].hp).toBe(500)
    expect(next.playerUnits[0].shield).toBe(2)
  })

  it('rejects shield-absorbed DoT ticks without canonical post_shield', () => {
    const shieldedState = {
      ...state,
      playerUnits: state.playerUnits.map(unit => ({ ...unit, shield: 10 }))
    }
    const next = applyCombatEvent(shieldedState, {
      type: 'damage_over_time_tick',
      unit_id: 'player_0',
      effect_id: 'dot-1',
      post_hp: 492,
      shield_absorbed: 8,
      seq: 9,
    }, { simTime: 1.0 })

    expect(next.playerUnits[0].hp).toBe(500)
    expect(next.playerUnits[0].shield).toBe(10)
  })

  describe('effect_applied events', () => {
    it('should install the canonical passive effect object by ID', () => {
      const event: CombatEvent = {
        type: 'effect_applied',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        effect_id: 'passive-effect-1',
        effect_type: 'mana_lock',
        effect: {
          id: 'passive-effect-1',
          type: 'mana_lock',
          duration: 2,
          expires_at: 3,
          source: 'caster',
          passive_effect: 'mana_lock'
        },
        seq: 1,
        timestamp: 1
      }

      const next = applyCombatEvent(state, event, { simTime: 1 })
      expect(next.playerUnits[0].effects).toEqual([
        expect.objectContaining({
          id: 'passive-effect-1',
          type: 'mana_lock',
          expiresAt: 3,
          passive_effect: 'mana_lock'
        })
      ])
      expect(state.playerUnits[0].effects).toEqual([])
    })

    it('rejects an effect without canonical type even when effect_type is present', () => {
      expect(() => applyCombatEvent(state, {
        type: 'effect_applied',
        unit_id: 'player_0',
        effect_id: 'missing-type',
        effect_type: 'mana_lock',
        effect: { id: 'missing-type' },
        seq: 2,
        timestamp: 2,
      }, { simTime: 2 })).toThrowError(CombatReplayValidationError)

      expect(state.playerUnits[0].effects).toEqual([])
    })

    it('rejects an effect whose canonical id does not match effect_id', () => {
      expect(() => applyCombatEvent(state, {
        type: 'effect_applied',
        unit_id: 'player_0',
        effect_id: 'payload-id',
        effect: { id: 'object-id', type: 'mana_lock' },
        seq: 3,
        timestamp: 3,
      }, { simTime: 3 })).toThrowError(CombatReplayValidationError)

      expect(state.playerUnits[0].effects).toEqual([])
    })
  })

  describe('item effect context', () => {
    it('keeps item identity, stack and before/after values on replay effects', () => {
      const next = applyCombatEvent(state, {
        type: 'stat_buff',
        unit_id: 'player_0',
        stat: 'defense',
        amount: 0.5,
        applied_delta: 0.5,
        effect_id: 'item-effect-1',
        item_id: 'fap_folder',
        item_effect_id: 'fap_folder:per_hit_received_stack',
        stack: 2,
        stacks: 2,
        stack_cap: 30,
        value_before: 1.5,
        value_after: 2,
        seq: 4,
        timestamp: 4,
      }, { simTime: 4 })

      expect(next.playerUnits[0].effects).toEqual([
        expect.objectContaining({
          item_id: 'fap_folder',
          item_effect_id: 'fap_folder:per_hit_received_stack',
          stack: 2,
          stacks: 2,
          stack_cap: 30,
          value_before: 1.5,
          value_after: 2,
        })
      ])
    })

    it('rejects partial item identity before mutating replay state', () => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState

      expect(() => applyCombatEvent(state, {
        type: 'effect_applied',
        unit_id: 'player_0',
        effect_id: 'item-effect-2',
        item_id: 'fap_folder',
        effect: { id: 'item-effect-2', type: 'item_effect' },
        seq: 5,
      }, { simTime: 5 })).toThrow('[REPLAY_VALIDATION] effect_applied event seq=5 item context requires non-empty string item_effect_id')

      expect(state).toEqual(original)
    })
  })

  describe('effect identity validation', () => {
    it.each(invalidEffectIds)('rejects invalid stat_buff effect_id: %p before mutation', (effectId) => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState

      expect(() => applyCombatEvent(state, {
        type: 'stat_buff', unit_id: 'player_0', stat: 'attack', amount: 2,
        applied_delta: 2, effect_id: effectId as string, seq: 40
      }, { simTime: 1 })).toThrowError(CombatReplayValidationError)
      expect(state).toEqual(original)
    })

    it.each(invalidEffectIds)('rejects invalid damage_over_time_tick effect_id: %p before mutation', (effectId) => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState

      expect(() => applyCombatEvent(state, {
        type: 'damage_over_time_tick', unit_id: 'player_0', post_hp: 490,
        effect_id: effectId as string, seq: 41
      }, { simTime: 1 })).toThrowError(CombatReplayValidationError)
      expect(state).toEqual(original)
    })

    it.each(invalidEffectIds)('rejects invalid shield_applied effect_id: %p before mutation', (effectId) => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState

      expect(() => applyCombatEvent(state, {
        type: 'shield_applied', unit_id: 'player_0', amount: 10, post_shield: 10,
        effect_id: effectId as string, seq: 42
      }, { simTime: 1 })).toThrowError(CombatReplayValidationError)
      expect(state).toEqual(original)
    })

    it.each(invalidEffectIds)('rejects invalid damage_over_time_applied effect_id: %p before mutation', (effectId) => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState

      expect(() => applyCombatEvent(state, {
        type: 'damage_over_time_applied', unit_id: 'player_0', damage: 5, expires_at: 3,
        effect_id: effectId as string, seq: 43
      }, { simTime: 1 })).toThrowError(CombatReplayValidationError)
      expect(state).toEqual(original)
    })

    it.each(invalidEffectIds)('rejects invalid damage_over_time_expired effect_id: %p before mutation', (effectId) => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState

      expect(() => applyCombatEvent(state, {
        type: 'damage_over_time_expired', unit_id: 'player_0', post_hp: 500,
        effect_id: effectId as string, seq: 44
      }, { simTime: 1 })).toThrowError(CombatReplayValidationError)
      expect(state).toEqual(original)
    })

    it.each(invalidEffectIds)('rejects invalid effect_expired effect_id: %p before mutation', (effectId) => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState

      expect(() => applyCombatEvent(state, {
        type: 'effect_expired', unit_id: 'player_0',
        effect_id: effectId as string, seq: 45
      }, { simTime: 1 })).toThrowError(CombatReplayValidationError)
      expect(state).toEqual(original)
    })

    it.each(invalidEffectIds)('rejects invalid unit_stunned effect_id: %p before mutation', (effectId) => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState

      expect(() => applyCombatEvent(state, {
        type: 'unit_stunned', unit_id: 'player_0', duration: 2,
        effect_id: effectId as string, seq: 46
      }, { simTime: 1 })).toThrowError(CombatReplayValidationError)
      expect(state).toEqual(original)
    })

    it('rejects an invalid embedded effect.id before mutation', () => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState

      expect(() => applyCombatEvent(state, {
        type: 'effect_applied', unit_id: 'player_0', effect_id: 'outer-id',
        effect: { id: 123, type: 'mana_lock' }, seq: 47
      }, { simTime: 1 })).toThrowError(CombatReplayValidationError)
      expect(state).toEqual(original)
    })

    it.each(invalidEffectIds)('rejects invalid effect_applied effect_id: %p before mutation', (effectId) => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState

      expect(() => applyCombatEvent(state, {
        type: 'effect_applied', unit_id: 'player_0', effect_id: effectId as string,
        effect: { id: 'embedded-id', type: 'mana_lock' }, seq: 48
      }, { simTime: 1 })).toThrowError(CombatReplayValidationError)
      expect(state).toEqual(original)
    })
  })

  describe('unit_stunned event identity', () => {
    it('rejects a stun without an effect ID before mutating state', () => {
      const original = JSON.parse(JSON.stringify(state)) as CombatState

      expect(() => applyCombatEvent(state, {
        type: 'unit_stunned',
        unit_id: 'player_0',
        duration: 2,
        seq: 30,
      }, { simTime: 1 })).toThrowError(CombatReplayValidationError)

      expect(() => applyCombatEvent(state, {
        type: 'unit_stunned',
        unit_id: 'player_0',
        duration: 2,
        effect_id: '   ',
        seq: 31,
      }, { simTime: 1 })).toThrow(
        '[REPLAY_VALIDATION] unit_stunned event seq=31 missing required effect_id'
      )
      expect(state).toEqual(original)
    })

    it('keeps the canonical stun ID so the matching expiration can remove it', () => {
      const stunned = applyCombatEvent(state, {
        type: 'unit_stunned',
        unit_id: 'player_0',
        duration: 2,
        effect_id: 'stun-1',
        seq: 32,
        timestamp: 1,
      }, { simTime: 1 })

      expect(stunned.playerUnits[0].effects).toEqual([
        expect.objectContaining({ id: 'stun-1', type: 'stun' })
      ])

      const expired = applyCombatEvent(stunned, {
        type: 'effect_expired',
        unit_id: 'player_0',
        effect_id: 'stun-1',
        seq: 33,
        timestamp: 3,
      }, { simTime: 3 })

      expect(expired.playerUnits[0].effects).toEqual([])
    })
  })

  describe('damage_over_time_applied events', () => {
    it('installs the canonical DoT payload and preserves server expiry', () => {
      const next = applyCombatEvent(state, {
        type: 'damage_over_time_applied',
        unit_id: 'player_0',
        effect_id: 'dot-1',
        damage: 10,
        amount: 999,
        duration: 2,
        interval: 1,
        ticks: 2,
        next_tick_time: 3,
        expires_at: 4,
        seq: 4,
        timestamp: 2,
      }, { simTime: 2 })

      expect(next.playerUnits[0].effects).toEqual([
        expect.objectContaining({
          id: 'dot-1',
          type: 'damage_over_time',
          damage: 10,
          expiresAt: 4,
          expires_at: 4,
          next_tick_time: 3,
        })
      ])
    })

    it('rejects the legacy amount alias when canonical damage is missing', () => {
      const next = applyCombatEvent(state, {
        type: 'damage_over_time_applied',
        unit_id: 'player_0',
        effect_id: 'dot-missing-damage',
        amount: 10,
        expires_at: 4,
        seq: 5,
        timestamp: 2,
      }, { simTime: 2 })

      expect(next.playerUnits[0].effects).toEqual([])
    })

    it('rejects a DoT application without canonical expiry', () => {
      const next = applyCombatEvent(state, {
        type: 'damage_over_time_applied',
        unit_id: 'player_0',
        effect_id: 'dot-missing-expiry',
        damage: 10,
        duration: 2,
        seq: 6,
        timestamp: 2,
      }, { simTime: 2 })

      expect(next.playerUnits[0].effects).toEqual([])
    })
  })

  describe('stat_buff events', () => {
    it('should add effect with proper ID from backend', () => {
      const event: CombatEvent = {
        type: 'stat_buff',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        stat: 'attack',
        value: 20,
        amount: 20,
        value_type: 'flat',
        duration: 5,
        permanent: false,
        effect_id: 'test-uuid-123',
        applied_delta: 20,
        seq: 1,
        timestamp: 1.0
      }

      const newState = applyCombatEvent(state, event, { simTime: 1.0 })

      const player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player).toBeDefined()
      expect(player!.effects).toHaveLength(1)
      expect(player!.effects![0]).toMatchObject({
        id: 'test-uuid-123',
        type: 'buff',
        stat: 'attack',
        value: 20,
        duration: 5
      })
    })

    it('should detect debuff by negative value', () => {
      const event: CombatEvent = {
        type: 'stat_buff',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        stat: 'defense',
        value: -15,
        amount: -15,
        value_type: 'flat',
        duration: 3,
        permanent: false,
        effect_id: 'debuff-uuid',
        applied_delta: -15,
        seq: 1,
        timestamp: 1.0
      }

      const newState = applyCombatEvent(state, event, { simTime: 1.0 })

      const player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.effects).toHaveLength(1)
      expect(player!.effects![0].type).toBe('debuff')
      expect(player!.effects![0].value).toBe(-15)
    })

    it('should apply stat changes correctly', () => {
      const event: CombatEvent = {
        type: 'stat_buff',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        stat: 'attack',
        value: 30,
        amount: 30,
        value_type: 'flat',
        duration: 5,
        permanent: false,
        effect_id: 'buff-uuid',
        applied_delta: 30,
        seq: 1,
        timestamp: 1.0
      }

      const newState = applyCombatEvent(state, event, { simTime: 1.0 })

      const player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.attack).toBe(80) // 50 + 30
      expect(player!.buffed_stats.attack).toBe(80)
    })

    it('should preserve the current health ratio when max HP changes', () => {
      const event: CombatEvent = {
        type: 'stat_buff',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        stat: 'max_hp',
        value: 10,
        amount: 10,
        value_type: 'percentage',
        duration: null,
        permanent: true,
        effect_id: 'max-hp-buff',
        applied_delta: 72,
        post_hp: 458,
        seq: 1,
        timestamp: 1.0
      }

      const damagedState = {
        ...state,
        playerUnits: state.playerUnits.map(unit => ({ ...unit, hp: 400 }))
      }
      const newState = applyCombatEvent(damagedState, event, { simTime: 1.0 })

      const player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.hp).toBe(458) // 80% of 572, rounded like the backend
      expect(player!.max_hp).toBe(572)
      expect(player!.buffed_stats.hp).toBe(572)
      expect(player!.effects![0]).toMatchObject({
        stat: 'max_hp',
        applied_delta: 72
      })
    })

    it('should not duplicate effects with same ID', () => {
      const event: CombatEvent = {
        type: 'stat_buff',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        stat: 'defense',
        value: 20,
        amount: 20,
        value_type: 'flat',
        duration: 5,
        permanent: false,
        effect_id: 'same-uuid',
        applied_delta: 20,
        seq: 1,
        timestamp: 1.0
      }

      // Apply same event twice
      let newState = applyCombatEvent(state, event, { simTime: 1.0 })

      newState = applyCombatEvent(newState, event, { simTime: 1.0 })

      const player = newState.playerUnits.find(u => u.id === 'player_0')

      expect(player!.effects).toHaveLength(1)
      expect(player!.defense).toBe(state.playerUnits[0].defense! + 20)
    })

    it('should store applied_delta for reversion', () => {
      const event: CombatEvent = {
        type: 'stat_buff',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        stat: 'defense',
        value: 25,
        amount: 25,
        value_type: 'flat',
        duration: 4,
        permanent: false,
        effect_id: 'revert-uuid',
        applied_delta: 25,
        seq: 1,
        timestamp: 1.0
      }

      const newState = applyCombatEvent(state, event, { simTime: 1.0 })

      const player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.effects![0].applied_delta).toBe(25)
    })

    it('should apply attack speed buffs and revert them from canonical post state', () => {
      const buffEvent: CombatEvent = {
        type: 'stat_buff',
        unit_id: 'player_0',
        stat: 'attack_speed',
        amount: 20,
        value_type: 'percentage_of_max',
        duration: 3,
        permanent: false,
        effect_id: 'attack-speed-buff',
        applied_delta: 0.2,
        seq: 1,
        timestamp: 1.0
      }

      let newState = applyCombatEvent(state, buffEvent, { simTime: 1.0 })
      let player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.attack_speed).toBeCloseTo(1.2)
      expect(player!.buffed_stats?.attack_speed).toBeCloseTo(1.2)

      newState = applyCombatEvent(newState, {
        type: 'effect_expired',
        unit_id: 'player_0',
        effect_id: 'attack-speed-buff',
        stat: 'attack_speed',
        post_attack_speed: 1.0,
        seq: 2,
        timestamp: 4.0
      }, { simTime: 4.0 })

      player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.attack_speed).toBeCloseTo(1.0)
      expect(player!.buffed_stats?.attack_speed).toBeCloseTo(1.0)
    })

    it('should not use an embedded snapshot to overwrite reducer state', () => {
      const newState = applyCombatEvent(state, {
        type: 'stat_buff',
        unit_id: 'opp_0',
        stat: 'attack_speed',
        amount: 20,
        value_type: 'percentage',
        effect_id: 'same-timestamp-buff',
        applied_delta: 0.2,
        game_state: {
          player_units: state.playerUnits,
          opponent_units: [{ ...state.opponentUnits[0], hp: 560, current_mana: 0 }]
        },
        seq: 701,
        timestamp: 7.95
      }, { simTime: 7.95 })

      const opponent = newState.opponentUnits.find(u => u.id === 'opp_0')
      expect(opponent!.hp).toBe(600)
      expect(opponent!.current_mana).toBe(0)
    })

    it('should not recover a dropped effect from a later event snapshot', () => {
      const newState = applyCombatEvent(state, {
        type: 'unit_attack',
        attacker_id: 'player_0',
        target_id: 'opp_0',
        target_hp: 560,
        attacker_current_mana: 20,
        game_state: {
          player_units: [{ ...state.playerUnits[0] }],
          opponent_units: [{
            ...state.opponentUnits[0],
            attack_speed: 1.2,
            buffed_stats: { ...state.opponentUnits[0].buffed_stats, attack_speed: 1.2 },
            effects: [{ id: 'recovered-speed-buff', type: 'buff', stat: 'attack_speed', value: 20, applied_delta: 0.2 }]
          }]
        },
        seq: 420,
        timestamp: 4.1
      }, { simTime: 4.1 })

      const opponent = newState.opponentUnits.find(u => u.id === 'opp_0')
      expect(opponent!.attack_speed).toBeCloseTo(1.0)
      expect(opponent!.effects).toHaveLength(0)
    })
  })

  describe('regen_gain events', () => {
    it('reconstructs the authoritative HP regeneration post-state', () => {
      const next = applyCombatEvent(state, {
        type: 'regen_gain',
        unit_id: 'opp_0',
        amount_per_sec: 6,
        total_amount: 30,
        duration: 5,
        post_hp_regen_per_sec: 6,
        seq: 147,
        timestamp: 12.5
      }, { simTime: 12.5 })

      expect(next.opponentUnits[0].buffed_stats?.hp_regen_per_sec).toBe(6)
      expect(next.regenMap.opp_0).toEqual({ amount_per_sec: 6, total_amount: 30, expiresAt: 17.5 })
      expect(state.opponentUnits[0].buffed_stats?.hp_regen_per_sec).toBe(0)
      expect(compareCombatStates(next, {
        player_units: next.playerUnits,
        opponent_units: [{
          ...next.opponentUnits[0],
          buffed_stats: { ...next.opponentUnits[0].buffed_stats, hp_regen_per_sec: 6 }
        }]
      }, {
        type: 'state_snapshot',
        seq: 148,
        timestamp: 12.5
      })).toEqual([])
    })

    it('rejects a regen event without the canonical post-state', () => {
      expect(() => applyCombatEvent(state, {
        type: 'regen_gain',
        unit_id: 'opp_0',
        amount_per_sec: 6,
        total_amount: 30,
        duration: 5,
        seq: 147
      }, { simTime: 12.5 })).toThrow('missing required post_hp_regen_per_sec')
    })
  })

  describe('effect_expired events', () => {
    it('replays the Set 2 regen lifecycle through seq=134 without a missing-effect crash', () => {
      let newState = applyCombatEvent(state, {
        type: 'effect_applied',
        unit_id: 'opp_0',
        effect_id: 'set2:opp_0:regen',
        effect_type: 'set2_regen_over_time',
        effect: {
          id: 'set2:opp_0:regen',
          type: 'set2_regen_over_time',
          amount_per_sec: 40,
          expires_at: 4,
          source: 'opp_0',
        },
        seq: 133,
        timestamp: 1,
      }, { simTime: 1 })

      newState = applyCombatEvent(newState, {
        type: 'effect_expired',
        unit_id: 'opp_0',
        effect_id: 'set2:opp_0:regen',
        effect_type: 'set2_regen_over_time',
        seq: 134,
        timestamp: 4,
      }, { simTime: 4 })

      expect(newState.opponentUnits[0].effects).toEqual([])
    })

    it('should remove effect and revert stats', () => {
      // First add a buff
      const buffEvent: CombatEvent = {
        type: 'stat_buff',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        stat: 'attack',
        value: 30,
        amount: 30,
        value_type: 'flat',
        duration: 5,
        permanent: false,
        effect_id: 'expiring-buff',
        applied_delta: 30,
        seq: 1,
        timestamp: 1.0
      }

      let newState = applyCombatEvent(state, buffEvent, { simTime: 1.0 })

      let player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.attack).toBe(80) // 50 + 30
      expect(player!.effects).toHaveLength(1)

      // Now expire the buff
      const expireEvent: CombatEvent = {
        type: 'effect_expired',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        effect_id: 'expiring-buff',
        stat: 'attack',
        post_attack: 50,
        seq: 2,
        timestamp: 6.0
      }

      newState = applyCombatEvent(newState, expireEvent, { simTime: 6.0 })

      player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.effects).toHaveLength(0)
      expect(player!.attack).toBe(50) // Back to original
    })

    it('should revert defense debuff correctly', () => {
      // Add debuff
      const debuffEvent: CombatEvent = {
        type: 'stat_buff',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        stat: 'defense',
        value: -10,
        amount: -10,
        value_type: 'flat',
        duration: 3,
        permanent: false,
        effect_id: 'defense-debuff',
        applied_delta: -10,
        seq: 1,
        timestamp: 1.0
      }

      let newState = applyCombatEvent(state, debuffEvent, { simTime: 1.0 })

      let player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.defense).toBe(15) // 25 - 10

      // Expire debuff
      const expireEvent: CombatEvent = {
        type: 'effect_expired',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        effect_id: 'defense-debuff',
        stat: 'defense',
        post_defense: 25,
        seq: 2,
        timestamp: 4.0
      }

      newState = applyCombatEvent(newState, expireEvent, { simTime: 4.0 })

      player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.defense).toBe(25) // Back to original
    })

    it('should reject expiration without the canonical post-stat value', () => {
      const buffEvent: CombatEvent = {
        type: 'stat_buff',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        stat: 'attack',
        value: 30,
        amount: 30,
        value_type: 'flat',
        duration: 5,
        permanent: false,
        effect_id: 'missing-post-attack',
        applied_delta: 30,
        seq: 1,
        timestamp: 1.0
      }

      const buffedState = applyCombatEvent(state, buffEvent, { simTime: 1.0 })

      expect(() => applyCombatEvent(buffedState, {
        type: 'effect_expired',
        unit_id: 'player_0',
        effect_id: 'missing-post-attack',
        stat: 'attack',
        seq: 2,
        timestamp: 6.0
      }, { simTime: 6.0 })).toThrow('Missing post_attack')
      expect(buffedState.playerUnits[0].attack).toBe(80)
      expect(buffedState.playerUnits[0].effects).toHaveLength(1)
    })

    it.each([
      { stat: 'defense', value: -10, appliedDelta: -10, postField: 'post_defense' },
      { stat: 'attack_speed', value: 20, appliedDelta: 0.2, postField: 'post_attack_speed' }
    ])('should reject $stat expiration without $postField', ({ stat, value, appliedDelta, postField }) => {
      const effectId = `missing-${stat}`
      const buffedState = applyCombatEvent(state, {
        type: 'stat_buff',
        unit_id: 'player_0',
        stat,
        value,
        amount: value,
        value_type: 'flat',
        duration: 5,
        permanent: false,
        effect_id: effectId,
        applied_delta: appliedDelta,
        seq: 1,
        timestamp: 1.0
      }, { simTime: 1.0 })
      const expiration = {
        type: 'effect_expired',
        unit_id: 'player_0',
        effect_id: effectId,
        stat,
        seq: 2,
        timestamp: 6.0
      } as CombatEvent
      delete (expiration as Record<string, unknown>)[postField]

      expect(() => applyCombatEvent(buffedState, expiration, { simTime: 6.0 })).toThrow(`Missing ${postField}`)
    })

    it('should reject HP expiration without canonical post_hp', () => {
      const buffedState = applyCombatEvent(state, {
        type: 'stat_buff',
        unit_id: 'player_0',
        stat: 'hp',
        value: 30,
        amount: 30,
        value_type: 'flat',
        duration: 5,
        permanent: false,
        effect_id: 'missing-post-hp',
        applied_delta: 30,
        seq: 1,
        timestamp: 1.0
      }, { simTime: 1.0 })

      expect(() => applyCombatEvent(buffedState, {
        type: 'effect_expired',
        unit_id: 'player_0',
        effect_id: 'missing-post-hp',
        stat: 'hp',
        seq: 2,
        timestamp: 6.0
      }, { simTime: 6.0 })).toThrow('Missing post_hp')
      expect(buffedState.playerUnits[0].hp).toBe(500)
      expect(buffedState.playerUnits[0].effects).toHaveLength(1)
    })

    it('should preserve the current health ratio when temporary max HP buffs expire', () => {
      const buffEvent: CombatEvent = {
        type: 'stat_buff',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        stat: 'max_hp',
        value: 10,
        amount: 10,
        value_type: 'percentage',
        duration: 3,
        permanent: false,
        effect_id: 'expiring-max-hp-buff',
        applied_delta: 72,
        post_hp: 458,
        seq: 1,
        timestamp: 1.0
      }

      const damagedState = {
        ...state,
        playerUnits: state.playerUnits.map(unit => ({ ...unit, hp: 400 }))
      }
      let newState = applyCombatEvent(damagedState, buffEvent, { simTime: 1.0 })

      let player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.hp).toBe(458)
      expect(player!.max_hp).toBe(572)
      expect(player!.buffed_stats.hp).toBe(572)

      newState = applyCombatEvent(newState, {
        type: 'effect_expired',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        effect_id: 'expiring-max-hp-buff',
        seq: 2,
        stat: 'max_hp',
        post_max_hp: 500,
        post_hp: 400,
        timestamp: 4.0
      }, { simTime: 4.0 })

      player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.hp).toBe(400) // 80% of the restored 500 max HP
      expect(player!.max_hp).toBe(500)
      expect(player!.buffed_stats.hp).toBe(500)
      expect(player!.effects).toHaveLength(0)
    })
  })

  describe('shield_applied events', () => {
    it('should add shield effect with ID', () => {
      const event: CombatEvent = {
        type: 'shield_applied',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        amount: 100,
        post_shield: 100,
        duration: 3,
        caster_name: 'Healer',
        effect_id: 'shield-uuid',
        seq: 1,
        timestamp: 1.0
      }

      const newState = applyCombatEvent(state, event, { simTime: 1.0 })

      const player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.shield).toBe(100)
      expect(player!.effects).toHaveLength(1)
      expect(player!.effects![0]).toMatchObject({
        id: 'shield-uuid',
        type: 'shield',
        amount: 100,
        duration: 3,
        caster_name: 'Healer'
      })
    })

    it('should remove the shield badge state when the matching effect expires', () => {
      let newState = applyCombatEvent(state, {
        type: 'shield_applied',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        amount: 100,
        post_shield: 100,
        duration: 3,
        effect_id: 'expiring-shield',
        seq: 1,
        timestamp: 1.0
      }, { simTime: 1.0 })

      newState = applyCombatEvent(newState, {
        type: 'effect_expired',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        effect_id: 'expiring-shield',
        effect_type: 'shield',
        post_shield: 0,
        seq: 2,
        timestamp: 4.0
      }, { simTime: 4.0 })

      const player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.shield).toBe(0)
      expect(player!.effects).toEqual([])
    })

    it('should reject shield expiration without canonical post_shield', () => {
      const shieldedState = applyCombatEvent(state, {
        type: 'shield_applied',
        unit_id: 'player_0',
        amount: 100,
        post_shield: 100,
        duration: 3,
        effect_id: 'missing-expiry-shield',
        seq: 1,
        timestamp: 1.0
      }, { simTime: 1.0 })

      expect(() => applyCombatEvent(shieldedState, {
        type: 'effect_expired',
        unit_id: 'player_0',
        effect_id: 'missing-expiry-shield',
        effect_type: 'shield',
        seq: 2,
        timestamp: 4.0
      }, { simTime: 4.0 })).toThrow('Missing post_shield')
      expect(shieldedState.playerUnits[0].shield).toBe(100)
      expect(shieldedState.playerUnits[0].effects).toHaveLength(1)
    })
  })

  describe('unit_stunned events', () => {
    it('should add stun effect with ID', () => {
      const event: CombatEvent = {
        type: 'unit_stunned',
        unit_id: 'opp_0',
        unit_name: 'TestOpponent',
        duration: 1.5,
        caster_name: 'Stunner',
        effect_id: 'stun-uuid',
        seq: 1,
        timestamp: 1.0
      }

      const newState = applyCombatEvent(state, event, { simTime: 1.0 })

      const opponent = newState.opponentUnits.find(u => u.id === 'opp_0')
      expect(opponent!.effects).toHaveLength(1)
      expect(opponent!.effects![0]).toMatchObject({
        id: 'stun-uuid',
        type: 'stun',
        duration: 1.5,
        caster_name: 'Stunner'
      })

      const expiredState = applyCombatEvent(newState, {
        type: 'effect_expired',
        unit_id: 'opp_0',
        unit_name: 'TestOpponent',
        effect_id: 'stun-uuid',
        seq: 2,
        timestamp: 3.0
      }, { simTime: 3.0 })

      expect(expiredState.opponentUnits.find(u => u.id === 'opp_0')!.effects).toEqual([])
    })
  })

  describe('Immutability - Deep Copy Validation', () => {
    it('should not mutate original state', () => {
      const originalState = { ...state }
      const originalPlayerUnit = { ...state.playerUnits[0] }

      const event: CombatEvent = {
        type: 'stat_buff',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        stat: 'attack',
        value: 20,
        amount: 20,
        value_type: 'flat',
        duration: 5,
        permanent: false,
        effect_id: 'immutable-test',
        applied_delta: 20,
        seq: 1,
        timestamp: 1.0
      }

      const newState = applyCombatEvent(state, event, { simTime: 1.0 })

      // Original state should be unchanged
      expect(state.playerUnits[0].effects).toHaveLength(0)
      expect(state.playerUnits[0].attack).toBe(originalPlayerUnit.attack)

      // New state should have changes
      expect(newState.playerUnits[0].effects).toHaveLength(1)
      expect(newState.playerUnits[0].attack).toBe(originalPlayerUnit.attack + 20)
    })

    it('should not share effects array references between states', () => {
      const event1: CombatEvent = {
        type: 'stat_buff',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        stat: 'attack',
        value: 10,
        amount: 10,
        value_type: 'flat',
        duration: 5,
        permanent: false,
        effect_id: 'effect-1',
        applied_delta: 10,
        seq: 1,
        timestamp: 1.0
      }

      const state1 = applyCombatEvent(state, event1, { simTime: 1.0 })

      const event2: CombatEvent = {
        type: 'stat_buff',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        stat: 'defense',
        value: 15,
        amount: 15,
        value_type: 'flat',
        duration: 5,
        permanent: false,
        effect_id: 'effect-2',
        applied_delta: 15,
        seq: 2,
        timestamp: 2.0
      }

      const state2 = applyCombatEvent(state1, event2, { simTime: 2.0 })

      // State1 should still have 1 effect, state2 should have 2
      expect(state1.playerUnits[0].effects).toHaveLength(1)
      expect(state2.playerUnits[0].effects).toHaveLength(2)

      // They should not share the same array reference
      expect(state1.playerUnits[0].effects).not.toBe(state2.playerUnits[0].effects)
    })
  })

  describe('Complex Effect Sequences', () => {
    it('should handle multiple buffs and debuffs correctly', () => {
      let currentState = state

      // Add attack buff
      currentState = applyCombatEvent(currentState, {
        type: 'stat_buff',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        stat: 'attack',
        value: 20,
        amount: 20,
        value_type: 'flat',
        duration: 5,
        permanent: false,
        effect_id: 'buff-1',
        applied_delta: 20,
        seq: 1,
        timestamp: 1.0
      }, { simTime: 1.0 })

      // Add defense debuff
      currentState = applyCombatEvent(currentState, {
        type: 'stat_buff',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        stat: 'defense',
        value: -10,
        amount: -10,
        value_type: 'flat',
        duration: 3,
        permanent: false,
        effect_id: 'debuff-1',
        applied_delta: -10,
        seq: 2,
        timestamp: 2.0
      }, { simTime: 2.0 })

      // Add shield
      currentState = applyCombatEvent(currentState, {
        type: 'shield_applied',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        amount: 50,
        post_shield: 50,
        duration: 4,
        caster_name: 'Healer',
        effect_id: 'shield-1',
        seq: 3,
        timestamp: 3.0
      }, { simTime: 3.0 })

      const player = currentState.playerUnits.find(u => u.id === 'player_0')

      expect(player!.effects).toHaveLength(3)
      expect(player!.attack).toBe(70) // 50 + 20
      expect(player!.defense).toBe(15) // 25 - 10
      expect(player!.shield).toBe(50)

      // Verify effect types
      const effectTypes = player!.effects!.map(e => e.type).sort()
      expect(effectTypes).toEqual(['buff', 'debuff', 'shield'])
    })

    it('rejects amount-only shield events without mutating shield state', () => {
      const newState = applyCombatEvent(state, {
        type: 'shield_applied',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        amount: 100,
        duration: 3,
        effect_id: 'amount-only-shield',
        seq: 10,
        timestamp: 1.0
      }, { simTime: 1.0 })

      const player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.shield).toBe(state.playerUnits.find(u => u.id === 'player_0')!.shield)
      expect(player!.effects).toEqual(state.playerUnits.find(u => u.id === 'player_0')!.effects)
    })

    it('rejects null canonical shield state without mutating shield state', () => {
      const newState = applyCombatEvent(state, {
        type: 'shield_applied',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        amount: 100,
        post_shield: null,
        duration: 3,
        effect_id: 'null-post-shield',
        seq: 11,
        timestamp: 1.0
      }, { simTime: 1.0 })

      const player = newState.playerUnits.find(u => u.id === 'player_0')
      expect(player!.shield).toBe(state.playerUnits.find(u => u.id === 'player_0')!.shield)
      expect(player!.effects).toEqual(state.playerUnits.find(u => u.id === 'player_0')!.effects)
    })
  })

  describe('Combat presentation summary', () => {
    it('should ignore late mana and attack events after unit death', () => {
      const died = applyCombatEvent(state, {
        type: 'unit_died', unit_id: 'player_0', unit_name: 'TestPlayer',
        seq: 20, timestamp: 3
      }, { simTime: 3 })

      const afterMana = applyCombatEvent(died, {
        type: 'mana_update', unit_id: 'player_0', current_mana: 80,
        max_mana: 100, amount: 80, seq: 21, timestamp: 3.1
      }, { simTime: 3.1 })
      const afterAttack = applyCombatEvent(afterMana, {
        type: 'unit_attack', attacker_id: 'player_0', target_id: 'opp_0',
        attacker_current_mana: 0, attacker_max_mana: 100, target_hp: 1,
        damage: 99, applied_damage: 99, seq: 22, timestamp: 3.2
      }, { simTime: 3.2 })

      expect(afterAttack.playerUnits[0].hp).toBe(0)
      expect(afterAttack.playerUnits[0].current_mana).toBe(0)
      expect(afterAttack.opponentUnits[0].hp).toBe(600)
      expect(afterAttack.combatSummary?.totalDamageByUnit['player_0']).toBeUndefined()
    })

    it('should apply authoritative current and max mana from mana_update', () => {
      state.playerUnits[0].current_mana = 70
      state.playerUnits[0].max_mana = 100

      const event: CombatEvent = {
        type: 'mana_update',
        unit_id: 'player_0',
        unit_name: 'TestPlayer',
        current_mana: 71,
        max_mana: 80,
        amount: 1,
        seq: 12,
        timestamp: 2.4
      }

      const newState = applyCombatEvent(state, event, { simTime: 2.4 })
      const unit = newState.playerUnits[0]

      expect(unit.current_mana).toBe(71)
      expect(unit.max_mana).toBe(80)
      expect(newState.combatLog.some(line => line.includes('[MANA]'))).toBe(false)
    })

    it('should clamp malformed mana above the authoritative maximum', () => {
      const event: CombatEvent = {
        type: 'mana_update',
        unit_id: 'player_0',
        current_mana: 999,
        max_mana: 40,
        amount: 999,
        seq: 13,
        timestamp: 2.5
      }

      const newState = applyCombatEvent(state, event, { simTime: 2.5 })
      expect(newState.playerUnits[0].current_mana).toBe(40)
      expect(newState.playerUnits[0].max_mana).toBe(40)
    })

    it('should track bonus attacks, focus and damage totals', () => {
      const event: CombatEvent = {
        type: 'unit_attack',
        attacker_id: 'player_0',
        attacker_name: 'TestPlayer',
        target_id: 'opp_0',
        target_name: 'TestOpponent',
        damage: 42,
        applied_damage: 42,
        attacker_current_mana: 0,
        attacker_max_mana: 100,
        target_hp: 158,
        bonus_attack: true,
        seq: 99,
        timestamp: 4.2
      }

      const newState = applyCombatEvent(state, event, { simTime: 4.2 })

      expect(newState.combatLog[newState.combatLog.length - 1]).toContain('[BONUS]')
      expect(newState.combatSummary?.bonusAttacks).toBe(1)
      expect(newState.combatSummary?.focus?.target_id).toBe('opp_0')
      expect(newState.combatSummary?.focus?.bonus_attack).toBe(true)
      expect(newState.combatSummary?.totalDamageByUnit['player_0'].damage).toBe(42)
      expect(newState.combatSummary?.lastAction?.type).toBe('unit_attack')
    })
  })
})
