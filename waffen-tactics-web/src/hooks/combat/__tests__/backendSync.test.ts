/**
 * Backend Synchronization Integration Test
 * 
 * Verifies UI event replay produces IDENTICAL state to backend's game_state.
 */

import { describe, it, expect } from 'vitest'
import { applyCombatEvent } from '../applyEvent'
import { CombatState, CombatEvent } from '../types'

interface BackendUnitState {
  id: string
  name: string
  hp: number
  max_hp: number
  attack: number
  defense: number
  current_mana: number
  max_mana: number
  shield: number
  effects: any[]
  buffed_stats?: { attack?: number, defense?: number }
}

interface BackendGameState {
  player_units: BackendUnitState[]
  opponent_units: BackendUnitState[]
}

function compareStates(ui: CombatState, backend: BackendGameState, seq: number): string[] {
  const diffs: string[] = []
  
  for (const b of backend.player_units) {
    const u = ui.playerUnits.find(x => x.id === b.id)
    if (!u) {
      diffs.push(`[${seq}] Missing player unit ${b.id}`)
      continue
    }
    
    const fields: (keyof BackendUnitState)[] = ['hp', 'max_hp', 'attack', 'defense', 'current_mana', 'shield']
    for (const f of fields) {
      if (u[f as keyof typeof u] !== b[f]) {
        diffs.push(`[${seq}] ${b.name}.${f}: UI=${u[f as keyof typeof u]} != Backend=${b[f]}`)
      }
    }
  }
  
  for (const b of backend.opponent_units) {
    const u = ui.opponentUnits.find(x => x.id === b.id)
    if (!u) {
      diffs.push(`[${seq}] Missing opponent unit ${b.id}`)
      continue
    }
    
    const fields: (keyof BackendUnitState)[] = ['hp', 'max_hp', 'attack', 'defense', 'current_mana', 'shield']
    for (const f of fields) {
      if (u[f as keyof typeof u] !== b[f]) {
        diffs.push(`[${seq}] ${b.name}.${f}: UI=${u[f as keyof typeof u]} != Backend=${b[f]}`)
      }
    }
  }
  
  return diffs
}

function initFromGameState(gs: BackendGameState): CombatState {
  return {
    playerUnits: gs.player_units.map(u => ({
      ...u,
      hp: u.hp ?? 0,
      current_mana: u.current_mana ?? 0,
      shield: u.shield ?? 0,
      effects: u.effects || []
    })),
    opponentUnits: gs.opponent_units.map(u => ({
      ...u,
      hp: u.hp ?? 0,
      current_mana: u.current_mana ?? 0,
      shield: u.shield ?? 0,
      effects: u.effects || []
    })),
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

describe('Backend Synchronization Test', () => {
  it('should maintain perfect sync between UI and backend', async () => {
    const path = '/home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend/test_events_with_snapshots_NEW.json'

    let events: (CombatEvent & { game_state?: BackendGameState })[]
    try {
      const fs = await import('fs')
      events = JSON.parse(fs.readFileSync(path, 'utf-8'))
    } catch {
      console.warn('⚠️ Backend event file not found - skipping')
      return
    }
    
    // Find first state_snapshot event to initialize
    const initEvent = events.find(e => e.type === 'state_snapshot')
    if (!initEvent) {
      throw new Error('No state_snapshot events found')
    }

    let ui = initFromGameState(initEvent as any)
    const allDiffs: string[] = []
    let checked = 0

    console.log(`\n🔍 Testing ${events.length} events...`)

    for (const event of events) {
      try {
        ui = applyCombatEvent(ui, event, { simTime: ui.simTime })
      } catch (err) {
        allDiffs.push(`[${event.seq}] ERROR: ${(err as Error).message}`)
        continue
      }

      if (event.type === 'state_snapshot') {
        checked++
        const diffs = compareStates(ui, event as any, event.seq || 0)
        if (diffs.length > 0) {
          allDiffs.push(`\n❌ DESYNC at seq=${event.seq} (${event.type}):\n${diffs.join('\n')}`)
        }
      }
    }
    
    console.log(`✅ Checked ${checked} snapshots`)
    
    if (allDiffs.length > 0) {
      console.error(`\n❌ Found ${allDiffs.length} desyncs:\n${allDiffs.slice(0, 10).join('\n')}`)
      if (allDiffs.length > 10) console.error(`\n... and ${allDiffs.length - 10} more`)
      expect(allDiffs).toEqual([])
    } else {
      console.log('✅ Perfect sync!')
    }
  })
  
  it('should detect missing required fields', () => {
    const events: (CombatEvent & { game_state?: BackendGameState })[] = [
      {
        type: 'state_snapshot',
        seq: 0,
        timestamp: 0,
        game_state: {
          player_units: [{ id: 'p1', name: 'Test', hp: 100, max_hp: 100, attack: 50, defense: 10, current_mana: 0, max_mana: 100, shield: 0, effects: [] }],
          opponent_units: [{ id: 'o1', name: 'Enemy', hp: 100, max_hp: 100, attack: 50, defense: 10, current_mana: 0, max_mana: 100, shield: 0, effects: [] }]
        }
      },
      {
        type: 'unit_attack',
        attacker_id: 'p1',
        target_id: 'o1',
        damage: 40,
        // MISSING: target_hp!
        seq: 1,
        timestamp: 0.5,
        game_state: {
          player_units: [{ id: 'p1', name: 'Test', hp: 100, max_hp: 100, attack: 50, defense: 10, current_mana: 0, max_mana: 100, shield: 0, effects: [] }],
          opponent_units: [{ id: 'o1', name: 'Enemy', hp: 60, max_hp: 100, attack: 50, defense: 10, current_mana: 0, max_mana: 100, shield: 0, effects: [] }]
        }
      }
    ]
    
    let ui = initFromGameState(events[0].game_state!)
    const errors: string[] = []
    const origError = console.error
    console.error = (...args: any[]) => {
      if (typeof args[0] === 'string' && args[0].includes('missing required field')) {
        errors.push(args[0])
      }
    }
    
    ui = applyCombatEvent(ui, events[1], { simTime: 0 })
    console.error = origError
    
    expect(errors.length).toBeGreaterThan(0)
    expect(errors[0]).toContain('target_hp')
    
    // HP should NOT be updated (event skipped)
    const opp = ui.opponentUnits.find(u => u.id === 'o1')
    expect(opp?.hp).toBe(100)
    
    // Desync should be detected
    const diffs = compareStates(ui, events[1].game_state!, 1)
    expect(diffs.length).toBeGreaterThan(0)
    expect(diffs[0]).toContain('Enemy.hp')
  })
})
