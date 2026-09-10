/**
 * Real Combat Event Replay Tests
 *
 * These tests load actual combat event dumps from the backend and replay them
 * through the frontend event handlers to validate:
 * - No crashes or errors during replay
 * - Effect IDs are properly tracked
 * - Effect types are correct (buff vs debuff)
 * - No effect duplication
 * - State matches backend snapshots (no desyncs)
 */

import { describe, it, expect } from 'vitest'
import { applyCombatEvent } from '../applyEvent'
import { compareCombatStates } from '../desync'
import { CombatState, CombatEvent } from '../types'
import fs from 'fs'
import path from 'path'

// Helper to load event dump from backend
function loadEventDump(filename: string): CombatEvent[] {
  const filepath = path.join(__dirname, '../../../../backend', filename)
  const content = fs.readFileSync(filepath, 'utf-8')
  return JSON.parse(content)
}

// Helper to create initial state from units_init event or game_state
function createStateFromUnitsInit(event: any): CombatState {
  return {
    playerUnits: event.player_units || [],
    opponentUnits: event.opponent_units || [],
    combatLog: [],
    isFinished: false,
    victory: null,
    finalState: null,
    synergies: event.synergies || {},
    traits: event.traits || [],
    opponentInfo: event.opponent || null,
    regenMap: {},
    simTime: 0,
    defeatMessage: undefined
  }
}

// Helper to initialize state from event dump (handles both old and new formats)
function initializeStateFromDump(events: any[]): CombatState | null {
  // Try to find units_init event (new format)
  const unitsInitEvent = events.find((e: any) => e.type === 'units_init')
  if (unitsInitEvent) {
    return createStateFromUnitsInit(unitsInitEvent)
  }

  // Fallback: Use first state_snapshot event (new dumps from combat_service)
  const firstSnapshot = events.find((e: any) => e.type === 'state_snapshot' && e.player_units)
  if (firstSnapshot) {
    return createStateFromUnitsInit(firstSnapshot)
  }

  // Fallback: Use first event with game_state (old format)
  const firstWithState = events.find((e: any) => e.game_state?.player_units)
  if (firstWithState && firstWithState.game_state) {
    return createStateFromUnitsInit(firstWithState.game_state)
  }

  // No valid initialization found
  return null
}

function createSyntheticEffectLifecycleEvents(): CombatEvent[] {
  const createUnit = (id: string) => ({
    id,
    name: id,
    hp: 100,
    max_hp: 100,
    attack: 50,
    defense: 10,
    attack_speed: 1,
    star_level: 1,
    position: 'front',
    effects: [],
    current_mana: 0,
    max_mana: 100,
    shield: 0,
    base_stats: { hp: 100, attack: 50, defense: 10, attack_speed: 1, max_mana: 100 },
    buffed_stats: { hp: 100, attack: 50, defense: 10, attack_speed: 1, max_mana: 100, hp_regen_per_sec: 0 }
  })

  return [
    {
      type: 'units_init',
      player_units: [createUnit('player_0')],
      opponent_units: [createUnit('opp_0')],
      seq: 1,
      timestamp: 0
    },
    {
      type: 'stat_buff',
      unit_id: 'player_0',
      stat: 'attack',
      amount: 5,
      value: 5,
      effect_id: 'stat-buff-1',
      applied_delta: 5,
      seq: 2,
      timestamp: 1
    },
    {
      type: 'shield_applied',
      unit_id: 'player_0',
      amount: 10,
      post_shield: 10,
      effect_id: 'shield-1',
      seq: 3,
      timestamp: 1
    },
    {
      type: 'effect_applied',
      unit_id: 'player_0',
      effect_id: 'generic-1',
      effect: { id: 'generic-1', type: 'mana_lock', duration: 4, expires_at: 5 },
      seq: 4,
      timestamp: 1
    },
    {
      type: 'unit_stunned',
      unit_id: 'player_0',
      effect_id: 'stun-1',
      duration: 1,
      seq: 5,
      timestamp: 1
    },
    {
      type: 'damage_over_time_applied',
      unit_id: 'player_0',
      effect_id: 'dot-1',
      damage: 3,
      duration: 3,
      interval: 1,
      ticks: 1,
      next_tick_time: 2,
      expires_at: 5,
      seq: 6,
      timestamp: 1
    },
    {
      type: 'damage_over_time_tick',
      unit_id: 'player_0',
      effect_id: 'dot-1',
      pre_hp: 100,
      post_hp: 97,
      shield_absorbed: 0,
      post_shield: 10,
      seq: 7,
      timestamp: 2
    },
    {
      type: 'effect_expired',
      unit_id: 'player_0',
      effect_id: 'stat-buff-1',
      stat: 'attack',
      post_attack: 50,
      seq: 8,
      timestamp: 3
    },
    {
      type: 'effect_expired',
      unit_id: 'player_0',
      effect_id: 'shield-1',
      effect_type: 'shield',
      post_shield: 0,
      seq: 9,
      timestamp: 3
    },
    {
      type: 'effect_expired',
      unit_id: 'player_0',
      effect_id: 'generic-1',
      seq: 10,
      timestamp: 5
    },
    {
      type: 'effect_expired',
      unit_id: 'player_0',
      effect_id: 'stun-1',
      seq: 11,
      timestamp: 2
    },
    {
      type: 'damage_over_time_expired',
      unit_id: 'player_0',
      effect_id: 'dot-1',
      post_hp: 97,
      seq: 12,
      timestamp: 5
    }
  ]
}

describe('Real Combat Event Replay - events_desync_team.json', () => {
  it('should replay all events without crashing', () => {
    const events = loadEventDump('events_desync_team.json')

    // Initialize state from dump (handles both old and new formats)
    const initialState = initializeStateFromDump(events)
    if (!initialState) {
      throw new Error('Could not initialize state from events_desync_team.json')
    }

    let state = initialState
    let simTime = 0

    // Replay all events
    for (const event of events) {
      if (!event.type || event.type === 'units_init') continue

      simTime = event.timestamp || simTime

      try {
        state = applyCombatEvent(state, event as CombatEvent, {
          
          simTime
        })
      } catch (error) {
        throw new Error(`Failed to apply event ${event.type} at seq ${event.seq}: ${error}`)
      }
    }

    // If we got here without crashes, the test passes
    expect(true).toBe(true)
  })

  it('should validate all stat_buff events have effect_id', () => {
    const events = loadEventDump('events_desync_team.json')

    const statBuffEvents = events.filter((e: any) => e.type === 'stat_buff')

    console.log(`\nChecking ${statBuffEvents.length} stat_buff events for effect_id...`)

    for (const event of statBuffEvents) {
      if (!event.effect_id) {
        console.error(`Missing effect_id in stat_buff event:`, JSON.stringify(event, null, 2))
      }
      expect(event.effect_id).toBeDefined()
      expect(event.effect_id).not.toBe(null)
      expect(event.effect_id).not.toBe(undefined)
    }
  })

  it('should validate effect types match value signs', () => {
    const events = loadEventDump('events_desync_team.json')

    const initialState = initializeStateFromDump(events)
    if (!initialState) {
      throw new Error('Could not initialize state from events_desync_team.json')
    }

    let state = initialState
    let simTime = 0

    const statBuffEvents = events.filter((e: any) => e.type === 'stat_buff')

    for (const event of statBuffEvents) {
      simTime = event.timestamp || simTime

      const stateBefore = state
      state = applyCombatEvent(state, event as CombatEvent, {
        
        simTime
      })

      // Find the unit that was buffed
      const allUnits = [...state.playerUnits, ...state.opponentUnits]
      const unit = allUnits.find(u => u.id === event.unit_id)

      if (!unit) continue

      // Find the newly added effect (should be the last one)
      const newEffect = unit.effects?.[unit.effects.length - 1]

      if (!newEffect) continue

      // Validate effect type matches value sign
      const value = event.value || event.amount || 0
      const expectedType = value < 0 ? 'debuff' : 'buff'

      if (newEffect.type !== expectedType) {
        console.error(`Effect type mismatch:`, {
          unit: unit.id,
          value,
          expectedType,
          actualType: newEffect.type,
          event: JSON.stringify(event, null, 2)
        })
      }

      expect(newEffect.type).toBe(expectedType)
    }
  })

  it('should detect desyncs between frontend and backend state', () => {
    const events = loadEventDump('events_desync_team.json')

    const initialState = initializeStateFromDump(events)
    if (!initialState) {
      throw new Error('Could not initialize state from events_desync_team.json')
    }

    let state = initialState
    let simTime = 0

    const allDesyncs: any[] = []

    // Replay events and check for desyncs at snapshots
    for (const event of events) {
      if (!event.type || event.type === 'units_init') continue

      simTime = event.timestamp || simTime

      state = applyCombatEvent(state, event as CombatEvent, {
        
        simTime
      })

      // If event has game_state snapshot, compare
      if (event.game_state) {
        const desyncs = compareCombatStates(state, event.game_state, event as CombatEvent)

        if (desyncs.length > 0) {
          allDesyncs.push(...desyncs.map(d => ({
            ...d,
            eventType: event.type,
            eventSeq: event.seq
          })))
        }
      }
    }

    // Log desyncs for debugging
    if (allDesyncs.length > 0) {
      console.log(`\n⚠️  Found ${allDesyncs.length} desyncs during replay:`)

      // Group by type
      const desyncsByType = allDesyncs.reduce((acc, d) => {
        const key = Object.keys(d.diff)[0]
        acc[key] = (acc[key] || 0) + 1
        return acc
      }, {} as Record<string, number>)

      console.log('Desync breakdown:', desyncsByType)

      // Show first few examples
      console.log('\nFirst 3 desyncs:')
      allDesyncs.slice(0, 3).forEach(d => {
        console.log(JSON.stringify(d, null, 2))
      })
    }

    // This test will fail if there are desyncs - that's the point!
    // Once all bugs are fixed, this should pass with 0 desyncs
    expect(allDesyncs.length).toBe(0)
  })

  it('should not create duplicate effects with same ID', () => {
    const events = loadEventDump('events_desync_team.json')

    const initialState = initializeStateFromDump(events)
    if (!initialState) {
      throw new Error('Could not initialize state from events_desync_team.json')
    }

    let state = initialState
    let simTime = 0

    for (const event of events) {
      if (!event.type || event.type === 'units_init') continue

      simTime = event.timestamp || simTime

      state = applyCombatEvent(state, event as CombatEvent, {
        
        simTime
      })

      // Check all units for duplicate effect IDs
      const allUnits = [...state.playerUnits, ...state.opponentUnits]

      for (const unit of allUnits) {
        if (!unit.effects || unit.effects.length === 0) continue

        const effectIds = unit.effects.map(e => e.id).filter(id => id !== undefined)
        const uniqueIds = new Set(effectIds)

        if (effectIds.length !== uniqueIds.size) {
          const duplicates = effectIds.filter((id, index) => effectIds.indexOf(id) !== index)

          console.error(`Duplicate effect IDs found on unit ${unit.id}:`, {
            duplicates,
            allEffects: unit.effects,
            atEvent: event.type,
            seq: event.seq
          })

          expect(effectIds.length).toBe(uniqueIds.size)
        }
      }
    }
  })
})

describe('Real Combat Event Replay - Diverse Team Compositions', () => {
  const testFiles = [
    { file: 'test_shield_heavy.json', desc: 'Shield-heavy teams' },
    { file: 'test_buff_heavy.json', desc: 'Buff-heavy teams' },
    { file: 'test_stun_heavy.json', desc: 'Stun-heavy teams' },
    { file: 'test_dot_heavy.json', desc: 'DoT-heavy teams' },
    { file: 'test_mixed_synergies.json', desc: 'Mixed synergies' },
    { file: 'test_high_stars.json', desc: 'High star levels' },
    { file: 'test_tank_vs_damage.json', desc: 'Tank vs Damage matchup' },
    { file: 'test_events_with_snapshots_NEW.json', desc: 'Canonical snapshot fixture' }
  ]

  testFiles.forEach(({ file, desc }) => {
    it(`should replay ${desc} (${file}) without errors`, () => {
      const events = loadEventDump(file)

      const initialState = initializeStateFromDump(events)
      if (!initialState) {
        throw new Error(`Could not initialize state from ${file}`)
      }

      let state = initialState
      let simTime = 0

      for (const event of events) {
        if (!event.type || event.type === 'units_init') continue

        simTime = event.timestamp || simTime

        try {
          state = applyCombatEvent(state, event as CombatEvent, {
            
            simTime
          })
        } catch (error) {
          throw new Error(`Failed to replay ${file} at event ${event.type} seq ${event.seq}: ${error}`)
        }
      }

      expect(true).toBe(true)
    })
  })
})

describe('Canonical synthetic effect replay', () => {
  it('replays effect application, tick, and expiration events with stable identities', () => {
    const events = createSyntheticEffectLifecycleEvents()
    const initialState = initializeStateFromDump(events)
    expect(initialState).not.toBeNull()

    let state = initialState!
    const appliedEffectIds = new Set<string>()
    const applicationTypes = new Set([
      'stat_buff',
      'shield_applied',
      'effect_applied',
      'unit_stunned',
      'damage_over_time_applied'
    ])

    for (const event of events) {
      if (event.type === 'units_init') continue

      state = applyCombatEvent(state, event, {
        simTime: event.timestamp || 0
      })

      if (applicationTypes.has(event.type)) {
        expect(typeof event.effect_id).toBe('string')
        const unit = [...state.playerUnits, ...state.opponentUnits].find(u => u.id === event.unit_id)
        expect(unit?.effects?.some(effect => effect.id === event.effect_id)).toBe(true)
        appliedEffectIds.add(event.effect_id!)
      }
    }

    expect(appliedEffectIds).toEqual(new Set([
      'stat-buff-1',
      'shield-1',
      'generic-1',
      'stun-1',
      'dot-1'
    ]))
    expect(state.playerUnits[0].attack).toBe(50)
    expect(state.playerUnits[0].shield).toBe(0)
    expect(state.playerUnits[0].hp).toBe(97)
    expect(state.playerUnits[0].effects).toEqual([])
  })
})

describe('Shared approved replay golden fixture', () => {
  it('replays the same canonical events used by the core and backend tests without desync', () => {
    const events = loadEventDump('test_fixtures/approved_replay_golden.json')
    const initialState = initializeStateFromDump(events)
    expect(initialState).not.toBeNull()

    let state = initialState!
    for (const event of events) {
      if (event.type === 'units_init') continue

      state = applyCombatEvent(state, event as CombatEvent, {
        simTime: event.timestamp || 0
      })

      if (event.type === 'state_snapshot') {
        expect(compareCombatStates(state, {
          player_units: event.player_units,
          opponent_units: event.opponent_units
        }, event as CombatEvent)).toEqual([])
      }
    }

    expect(state.opponentUnits.find(unit => unit.id === 'opp_front')?.hp).toBe(0)
    expect(state.opponentUnits.find(unit => unit.id === 'opp_back')?.hp).toBe(80)
    expect(state.playerUnits.find(unit => unit.id === 'p_front')?.current_mana).toBe(10)
  })

  it('reports a desync when a canonical mutation event is omitted', () => {
    const events = loadEventDump('test_fixtures/approved_replay_golden.json')
      .filter(event => event.seq !== 6)
    const initialState = initializeStateFromDump(events)
    expect(initialState).not.toBeNull()

    let state = initialState!
    let desyncs: ReturnType<typeof compareCombatStates> = []
    for (const event of events) {
      if (event.type === 'units_init') continue

      state = applyCombatEvent(state, event as CombatEvent, {
        simTime: event.timestamp || 0
      })

      if (event.type === 'state_snapshot') {
        desyncs = compareCombatStates(state, {
          player_units: event.player_units,
          opponent_units: event.opponent_units
        }, event as CombatEvent)
      }
    }

    expect(desyncs).toEqual(expect.arrayContaining([
      expect.objectContaining({
        unit_id: 'opp_back',
        diff: expect.objectContaining({
          hp: { ui: 100, server: 80 }
        })
      })
    ]))
  })
})
