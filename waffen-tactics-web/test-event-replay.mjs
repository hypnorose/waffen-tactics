/**
 * Event Replay Validation Test
 *
 * This script validates that the frontend applyEvent logic correctly reconstructs
 * combat state from backend event streams.
 *
 * Usage:
 *   node test-event-replay.mjs <path-to-event-stream.json>
 *
 * Event stream format (JSONL - one event per line):
 *   {"type": "start", "seq": 1, "timestamp": 0.0}
 *   {"type": "units_init", "seq": 2, "player_units": [...], ...}
 *   {"type": "state_snapshot", "seq": 10, "game_state": {...}, ...}
 *   ...
 */

import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// ============================================================================
// Import Frontend Logic (TypeScript will be transpiled by ts-node or similar)
// ============================================================================
// NOTE: For now, we'll inline the applyEvent logic. In production, you could:
// 1. Use ts-node to import directly
// 2. Build the TS files first
// 3. Use tsx or esbuild for runtime transpilation

// Inline applyEvent logic from src/hooks/combat/applyEvent.ts
function applyCombatEvent(state, event, ctx) {
  let newState = { ...state }

  // Update simTime if timestamp present
  if (typeof event.timestamp === 'number') {
    newState.simTime = event.timestamp
  }

  switch (event.type) {
    case 'start':
      newState.combatLog = [...newState.combatLog, '⚔️ Walka rozpoczyna się!']
      break

    case 'units_init':
      if (event.player_units) {
        const normalizedPlayers = event.player_units.map((u, idx) => ({
          ...u,
          hp: u.hp ?? 0,
          current_mana: u.current_mana ?? 0,
          shield: u.shield ?? 0,
          position: u.position ?? (idx < Math.ceil(event.player_units.length / 2) ? 'front' : 'back'),
          effects: u.effects || []
        }))
        newState.playerUnits = normalizedPlayers
      }
      if (event.opponent_units) {
        const normalizedOpps = event.opponent_units.map((u, idx) => ({
          ...u,
          hp: u.hp ?? 0,
          current_mana: u.current_mana ?? 0,
          shield: u.shield ?? 0,
          position: u.position ?? (idx < Math.ceil(event.opponent_units.length / 2) ? 'front' : 'back'),
          effects: u.effects || []
        }))
        newState.opponentUnits = normalizedOpps
      }
      if (event.synergies) newState.synergies = event.synergies
      if (event.traits) newState.traits = event.traits
      if (event.opponent) newState.opponentInfo = event.opponent
      break

    case 'state_snapshot':
      // Expire effects based on current simulation time
      const currentTime = ctx.simTime
      newState.playerUnits = newState.playerUnits.map(u => ({
        ...u,
        effects: u.effects?.filter(e => !e.expiresAt || e.expiresAt > currentTime) || []
      }))
      newState.opponentUnits = newState.opponentUnits.map(u => ({
        ...u,
        effects: u.effects?.filter(e => !e.expiresAt || e.expiresAt > currentTime) || []
      }))

      // Update metadata that doesn't come from events
      if (event.synergies) newState.synergies = event.synergies
      if (event.traits) newState.traits = event.traits
      if (event.opponent) newState.opponentInfo = event.opponent
      break

    case 'attack':
      const targetId = event.target_id
      const targetHp = event.target_hp
      const shieldAbsorbed = event.shield_absorbed || 0
      const side = event.side
      if (targetId && typeof targetHp === 'number' && side) {
        if (side === 'team_a') {
          newState.playerUnits = updateUnitById(newState.playerUnits, targetId, u => ({
            ...u,
            hp: targetHp,
            shield: Math.max(0, (u.shield || 0) - shieldAbsorbed)
          }))
        } else {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, targetId, u => ({
            ...u,
            hp: targetHp,
            shield: Math.max(0, (u.shield || 0) - shieldAbsorbed)
          }))
        }
      }
      break

    case 'unit_attack':
      if (event.target_id) {
        let newHp
        if (event.unit_hp !== undefined) {
          newHp = event.unit_hp
        } else if (event.target_hp !== undefined) {
          newHp = event.target_hp
        } else if (event.post_hp !== undefined) {
          newHp = event.post_hp
        } else if (event.new_hp !== undefined) {
          newHp = event.new_hp
        }

        const shieldAbsorbed = event.shield_absorbed || 0

        if (newHp !== undefined) {
          const updateFn = (u) => {
            const newShield = Math.max(0, (u.shield || 0) - shieldAbsorbed)
            return { ...u, hp: newHp, shield: newShield }
          }
          if (event.target_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.target_id, updateFn)
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.target_id, updateFn)
          }
        } else if (event.damage !== undefined) {
          const damage = event.damage
          const hpDamage = damage - shieldAbsorbed
          const updateFn = (u) => {
            const oldHp = u.hp
            const calcHp = Math.max(0, oldHp - hpDamage)
            const newShield = Math.max(0, (u.shield || 0) - shieldAbsorbed)
            return { ...u, hp: calcHp, shield: newShield }
          }
          if (event.target_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.target_id, updateFn)
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.target_id, updateFn)
          }
        }
      }
      const msg = event.is_skill
        ? `🔥 ${event.attacker_name} zadaje ${event.damage?.toFixed(2)} obrażeń ${event.target_name} (umiejętność)`
        : `⚔️ ${event.attacker_name} atakuje ${event.target_name} (${(event.damage ?? 0).toFixed(2)} dmg)`
      newState.combatLog = [...newState.combatLog, msg]
      break

    case 'unit_died':
      if (event.unit_id) {
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, u => ({ ...u, hp: 0 }))
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, u => ({ ...u, hp: 0 }))
        }
      }
      newState.combatLog = [...newState.combatLog, `💀 ${event.unit_name} zostaje pokonany!`]
      break

    case 'stat_buff':
      const statName = event.stat === 'attack' ? 'Ataku' : event.stat === 'defense' ? 'Obrony' : event.stat || 'Statystyki'
      const buffType = event.buff_type === 'debuff' ? '⬇️' : '⬆️'
      let reason = ''
      if (event.buff_type === 'debuff') reason = '(umiejętność)'
      else if (event.cause === 'kill') reason = '(zabity wróg)'
      const buffMsg = `${buffType} ${event.unit_name} ${event.buff_type === 'debuff' ? 'traci' : 'zyskuje'} ${event.amount} ${statName} ${reason}`
      newState.combatLog = [...newState.combatLog, buffMsg]
      if (event.unit_id) {
        const amountNum = event.amount ?? 0
        let delta = 0

        if (event.applied_delta !== undefined) {
          delta = event.applied_delta
        } else if (event.stat !== 'random') {
          if (event.value_type === 'percentage') {
            const baseStat = event.stat === 'hp' ? 0 : (event.stat === 'attack' ? (event.unit_attack ?? 0) : (event.unit_defense ?? 0))
            delta = Math.floor(baseStat * (amountNum / 100))
          } else {
            delta = amountNum
          }
        }
        const effectType = event.buff_type === 'debuff' ? 'debuff' : 'buff'
        const effect = {
          type: effectType,
          stat: event.stat,
          value: amountNum,
          value_type: event.value_type,
          duration: event.duration,
          permanent: event.permanent,
          source: event.source_id,
          expiresAt: event.duration ? ctx.simTime + event.duration : undefined,
          applied_delta: delta
        }
        const updateFn = (u) => {
          let newU = { ...u, effects: [...(u.effects || []), effect] }
          if (event.stat === 'hp') {
            newU.hp = Math.min(u.max_hp, u.hp + delta)
          } else if (event.stat === 'attack') {
            newU.attack = u.attack + delta
            newU.buffed_stats = { ...u.buffed_stats, attack: newU.attack }
          } else if (event.stat === 'defense') {
            newU.defense = (u.defense ?? 0) + delta
            newU.buffed_stats = { ...u.buffed_stats, defense: newU.defense }
          }
          return newU
        }
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
        }
      }
      break

    case 'mana_update':
      if (event.unit_id) {
        if (event.current_mana !== undefined && event.current_mana !== null) {
          const updateFn = (u) => ({ ...u, current_mana: event.current_mana })
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
          }
          newState.combatLog = [...newState.combatLog, `🔮 ${event.unit_name} mana: ${event.current_mana}/${event.max_mana}`]
        } else if (event.amount !== undefined) {
          const amountNum = event.amount ?? 0
          const updateFn = (u) => {
            const cur = u.current_mana ?? 0
            const max = u.max_mana ?? Number.POSITIVE_INFINITY
            const newMana = Math.min(max, cur + amountNum)
            return { ...u, current_mana: newMana }
          }
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
          }
        }
      }
      break

    case 'victory':
      newState.combatLog = [...newState.combatLog, '🎉 ZWYCIĘSTWO!']
      newState.victory = true
      break

    case 'defeat':
      newState.combatLog = [...newState.combatLog, event.message || '💔 PRZEGRANA!']
      newState.victory = false
      newState.defeatMessage = event.message
      break

    case 'end':
      newState.isFinished = true
      if (event.state) {
        newState.finalState = event.state
        if (event.state.player_units) {
          newState.playerUnits = event.state.player_units.map((u) => ({
            ...u,
            hp: u.hp,
            max_hp: u.max_hp,
            current_mana: u.current_mana,
            shield: u.shield,
            effects: u.effects || []
          }))
        }
        if (event.state.opponent_units) {
          newState.opponentUnits = event.state.opponent_units.map((u) => ({
            ...u,
            hp: u.hp,
            max_hp: u.max_hp,
            current_mana: u.current_mana,
            shield: u.shield,
            effects: u.effects || []
          }))
        }
      }
      break

    case 'heal':
    case 'unit_heal':
      const healUnitId = event.unit_id
      const healSide = event.side
      if (healUnitId) {
        let newHealHp
        if (event.unit_hp !== undefined) {
          newHealHp = event.unit_hp
        } else if (event.post_hp !== undefined) {
          newHealHp = event.post_hp
        } else if (event.new_hp !== undefined) {
          newHealHp = event.new_hp
        }

        if (newHealHp !== undefined) {
          const updateFn = (u) => ({ ...u, hp: newHealHp })
          if (healSide === 'team_a' || !healUnitId.startsWith('opp_')) {
            newState.playerUnits = updateUnitById(newState.playerUnits, healUnitId, updateFn)
          } else {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, healUnitId, updateFn)
          }
        } else if (event.amount !== undefined) {
          const healAmount = event.amount
          const updateFn = (u) => ({ ...u, hp: Math.min(u.max_hp, u.hp + healAmount) })
          if (healSide === 'team_a' || !healUnitId.startsWith('opp_')) {
            newState.playerUnits = updateUnitById(newState.playerUnits, healUnitId, updateFn)
          } else {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, healUnitId, updateFn)
          }
        }
      }
      newState.combatLog = [...newState.combatLog, `💚 ${event.unit_name} regeneruje ${(event.amount ?? 0).toFixed(2)} HP`]
      break

    case 'hp_regen':
      if (event.unit_id) {
        if (event.unit_hp !== undefined) {
          const updateFn = (u) => ({ ...u, hp: event.unit_hp })
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
          }
        } else if (event.post_hp !== undefined) {
          const updateFn = (u) => ({ ...u, hp: event.post_hp })
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
          }
        }
      }
      if ((event.amount ?? 0) >= 1) {
        newState.combatLog = [...newState.combatLog, `💚 ${event.unit_name} regeneruje ${(event.amount ?? 0).toFixed(2)} HP (${event.cause || 'passive'})`]
      }
      break

    case 'damage_over_time_tick':
      if (event.unit_id) {
        const updateFn = (u) => ({ ...u, hp: event.unit_hp ?? u.hp })
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
        }
      }
      newState.combatLog = [...newState.combatLog, `🔥 ${event.unit_name} otrzymuje ${event.damage ?? 0} obrażeń (DoT)`]
      break

    case 'skill_cast':
      if (event.target_id && event.target_hp !== undefined) {
        if (event.target_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.target_id, u => ({ ...u, hp: event.target_hp }))
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.target_id, u => ({ ...u, hp: event.target_hp }))
        }
      }
      newState.combatLog = [...newState.combatLog, `✨ ${event.caster_name} używa ${event.skill_name}!`]
      break

    case 'shield_applied':
      if (event.unit_id && typeof event.amount === 'number') {
        const updateFn = (u) => {
          const newShield = (u.shield || 0) + event.amount
          const effect = {
            type: 'shield',
            amount: event.amount,
            duration: event.duration,
            caster_name: event.caster_name,
            expiresAt: event.duration ? ctx.simTime + event.duration : undefined,
            applied_amount: event.amount
          }
          return { ...u, effects: [...(u.effects || []), effect], shield: Math.max(0, newShield) }
        }
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
        }
      }
      newState.combatLog = [...newState.combatLog, `🛡️ ${event.unit_name} zyskuje ${event.amount} tarczy na ${event.duration}s`]
      break

    case 'unit_stunned':
      newState.combatLog = [...newState.combatLog, `😵 ${event.unit_name} jest ogłuszony na ${event.duration}s`]
      if (event.unit_id) {
        const effect = {
          type: 'stun',
          duration: event.duration,
          caster_name: event.caster_name,
          expiresAt: event.duration ? ctx.simTime + event.duration : undefined
        }
        const updateFn = (u) => ({ ...u, effects: [...(u.effects || []), effect] })
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
        }
      }
      break

    case 'damage_over_time_applied':
      newState.combatLog = [...newState.combatLog, `🔥 ${event.unit_name} otrzymuje DoT (${event.ticks || '?'} ticks)`]
      if (event.unit_id) {
        const effect = {
          type: 'damage_over_time',
          damage: event.damage || event.amount,
          duration: event.duration,
          ticks: event.ticks,
          interval: event.interval,
          caster_name: event.caster_name,
          expiresAt: event.duration ? ctx.simTime + event.duration : undefined
        }
        const updateFn = (u) => ({ ...u, effects: [...(u.effects || []), effect] })
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
        }
      }
      break

    case 'damage_over_time_expired':
    case 'effect_expired':
      if (event.unit_id) {
        const removeEffectFn = (u) => ({
          ...u,
          effects: u.effects?.filter(e => e.id !== event.effect_id) || []
        })
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, removeEffectFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, removeEffectFn)
        }
        if (event.unit_hp !== undefined) {
          const updateHpFn = (u) => ({ ...u, hp: event.unit_hp })
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateHpFn)
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateHpFn)
          }
        }
      }
      break
  }

  // IMPORTANT: Do NOT auto-expire effects here!
  // Effects should ONLY be removed when effect_expired events arrive from backend.
  // Auto-expiration causes desyncs because frontend timing may differ from backend by a few ms.

  return newState
}

function updateUnitById(units, id, updater) {
  return units.map(u => u.id === id ? updater(u) : u)
}

// ============================================================================
// State Comparison Logic (from desync.ts)
// ============================================================================
function compareCombatStates(uiState, serverState, seq, timestamp) {
  const diffs = []

  const compareUnit = (uiUnit, serverUnit, unitId) => {
    const diff = {}

    // HP comparison with tolerance for floating point
    const hpDiff = Math.abs(uiUnit.hp - serverUnit.hp)
    if (hpDiff > 0.01) {
      diff.hp = { ui: uiUnit.hp, server: serverUnit.hp }
    }

    // Mana comparison
    const manaDiff = Math.abs((uiUnit.current_mana ?? 0) - (serverUnit.current_mana ?? 0))
    if (manaDiff > 0.01) {
      diff.current_mana = { ui: uiUnit.current_mana, server: serverUnit.current_mana }
    }

    // Shield comparison
    const shieldDiff = Math.abs((uiUnit.shield ?? 0) - (serverUnit.shield ?? 0))
    if (shieldDiff > 0.01) {
      diff.shield = { ui: uiUnit.shield, server: serverUnit.shield }
    }

    // Attack comparison
    const attackDiff = Math.abs((uiUnit.attack ?? 0) - (serverUnit.attack ?? 0))
    if (attackDiff > 0.01) {
      diff.attack = { ui: uiUnit.attack, server: serverUnit.attack }
    }

    // Defense comparison
    const defenseDiff = Math.abs((uiUnit.defense ?? 0) - (serverUnit.defense ?? 0))
    if (defenseDiff > 0.01) {
      diff.defense = { ui: uiUnit.defense, server: serverUnit.defense }
    }

    if (Object.keys(diff).length > 0) {
      diffs.push({
        unit_id: unitId,
        unit_name: uiUnit.name,
        seq,
        timestamp,
        diff,
        pending_events: []
      })
    }
  }

  // Compare player units
  uiState.playerUnits.forEach(uiUnit => {
    const serverUnit = serverState.player_units?.find(u => u.id === uiUnit.id)
    if (serverUnit) {
      compareUnit(uiUnit, serverUnit, uiUnit.id)
    }
  })

  // Compare opponent units
  uiState.opponentUnits.forEach(uiUnit => {
    const serverUnit = serverState.opponent_units?.find(u => u.id === uiUnit.id)
    if (serverUnit) {
      compareUnit(uiUnit, serverUnit, uiUnit.id)
    }
  })

  return diffs
}

// ============================================================================
// Main Test Logic
// ============================================================================
function createInitialState() {
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
    simTime: 0
  }
}

function loadEventStream(filepath) {
  const content = fs.readFileSync(filepath, 'utf-8')

  // Support both JSONL (one event per line) and JSON array
  if (content.trim().startsWith('[')) {
    return JSON.parse(content)
  } else {
    return content.trim().split('\n').filter(l => l.trim()).map(line => JSON.parse(line))
  }
}

function validateEventStream(events) {
  console.log(`\n${'='.repeat(80)}`)
  console.log(`VALIDATING EVENT STREAM`)
  console.log(`${'='.repeat(80)}\n`)
  console.log(`Total events: ${events.length}`)

  let state = createInitialState()
  let totalDesyncs = 0
  const desyncsByEvent = []

  events.forEach((event, idx) => {
    const ctx = {
      overwriteSnapshots: false,
      simTime: state.simTime
    }

    // Apply event
    state = applyCombatEvent(state, event, ctx)

    // CRITICAL: Validate game_state on EVERY event (not just state_snapshot)
    // The web backend adds game_state to every event for validation
    if (event.game_state) {
      const diffs = compareCombatStates(state, event.game_state, event.seq, event.timestamp)

      if (diffs.length > 0) {
        totalDesyncs += diffs.length
        desyncsByEvent.push({
          eventIndex: idx,
          eventType: event.type,
          seq: event.seq,
          timestamp: event.timestamp,
          diffs
        })

        console.log(`\n⚠️  DESYNC DETECTED at event #${idx} type=${event.type} (seq=${event.seq}, t=${event.timestamp?.toFixed(2)}s)`)
        diffs.forEach(d => {
          console.log(`   Unit: ${d.unit_name} (${d.unit_id})`)
          Object.entries(d.diff).forEach(([key, values]) => {
            console.log(`      ${key}: UI=${values.ui} vs Server=${values.server}`)
          })
        })
      }
    }
  })

  console.log(`\n${'='.repeat(80)}`)
  console.log(`VALIDATION SUMMARY`)
  console.log(`${'='.repeat(80)}\n`)

  if (totalDesyncs === 0) {
    console.log(`✅ SUCCESS: No desyncs detected!`)
    console.log(`   All ${events.length} events applied correctly.`)
  } else {
    console.log(`❌ FAILED: ${totalDesyncs} desyncs across ${desyncsByEvent.length} snapshots`)
    console.log(`\n   Desyncs by snapshot:`)
    desyncsByEvent.forEach(({ eventIndex, seq, timestamp, diffs }) => {
      console.log(`      Event #${eventIndex} (seq=${seq}, t=${timestamp?.toFixed(2)}s): ${diffs.length} unit(s)`)
    })
  }

  console.log(`\n${'='.repeat(80)}\n`)

  return {
    success: totalDesyncs === 0,
    totalDesyncs,
    desyncsByEvent,
    finalState: state
  }
}

// ============================================================================
// CLI Entry Point
// ============================================================================
function main() {
  const args = process.argv.slice(2)

  if (args.length === 0) {
    console.error('Usage: node test-event-replay.mjs <path-to-event-stream.json>')
    console.error('\nEvent stream format: JSONL (one event per line) or JSON array')
    console.error('Each event must have "type" field, snapshots should have "game_state" field')
    process.exit(1)
  }

  const filepath = path.resolve(args[0])

  if (!fs.existsSync(filepath)) {
    console.error(`Error: File not found: ${filepath}`)
    process.exit(1)
  }

  console.log(`Loading event stream from: ${filepath}`)

  try {
    const events = loadEventStream(filepath)
    const result = validateEventStream(events)

    process.exit(result.success ? 0 : 1)
  } catch (error) {
    console.error(`\n❌ ERROR: ${error.message}`)
    console.error(error.stack)
    process.exit(1)
  }
}

main()
