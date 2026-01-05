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

describe('Real Combat Event Replay - events_desync_team.json', () => {
  it('should replay all events without crashing', () => {
    const events = loadEventDump('events_desync_team.json')

    // Initialize state from dump (handles both old and new formats)
    const initialState = initializeStateFromDump(events)
    if (!initialState) {
      console.warn('Could not initialize state from events_desync_team.json, skipping test')
      return
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
      console.warn('Could not initialize state, skipping test')
      return
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
      console.warn('Could not initialize state, skipping test')
      return
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
      console.warn('Could not initialize state, skipping test')
      return
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
    { file: 'test_tank_vs_damage.json', desc: 'Tank vs Damage matchup' }
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

describe('Effect ID Validation', () => {
  it('should verify all effect events have proper UUIDs', () => {
    // Use fresh dump that has shield effect_id fix applied
    const events = loadEventDump('events_test_fresh.json')

    const effectEventTypes = ['stat_buff', 'shield_applied', 'unit_stunned', 'damage_over_time_applied']
    const effectEvents = events.filter((e: any) => effectEventTypes.includes(e.type))

    console.log(`\nValidating effect_id format for ${effectEvents.length} effect events...`)

    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

    for (const event of effectEvents) {
      if (!event.effect_id) {
        console.error(`Missing effect_id in ${event.type} event at seq ${event.seq}`)
        expect(event.effect_id).toBeDefined()
      }

      if (!uuidRegex.test(event.effect_id)) {
        console.error(`Invalid UUID format for effect_id in ${event.type}:`, event.effect_id)
        expect(uuidRegex.test(event.effect_id)).toBe(true)
      }
    }
  })
})
