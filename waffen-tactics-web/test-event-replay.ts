/**
 * TypeScript Event Replay Test
 *
 * Tests the frontend applyEvent logic by replaying events from combat simulator.
 * Generates events using the backend combat simulator and compares reconstructed
 * state with authoritative backend state snapshots.
 *
 * Usage:
 *   npx tsx test-event-replay.ts [seed]
 *
 * Examples:
 *   npx tsx test-event-replay.ts 5
 *   npx tsx test-event-replay.ts  # Uses random seed
 */

import * as fs from 'fs'
import * as path from 'path'
import { spawn } from 'child_process'
import { fileURLToPath } from 'url'
import { applyCombatEvent } from './src/hooks/combat/applyEvent'
import { compareCombatStates } from './src/hooks/combat/desync'
import { CombatState, CombatEvent } from './src/hooks/combat/types'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// Initial empty combat state
function createInitialState(): CombatState {
  return {
    playerUnits: [],
    opponentUnits: [],
    synergies: {},
    traits: [],
    combatLog: [],
    simTime: 0,
    opponentInfo: { name: '', wins: 0, level: 0 }
  }
}

// Generate events using the backend combat simulator
function generateEventsWithSimulator(seed?: number): Promise<CombatEvent[]> {
  return new Promise((resolve, reject) => {
    const scriptPath = path.resolve(__dirname, 'backend/save_combat_events.py')
    const args = seed ? [seed.toString()] : ['--random']

    console.log(`Running combat simulator with args: ${args.join(' ')}`)

    const pythonProcess = spawn('/usr/bin/python3', [scriptPath, ...args], {
      cwd: path.dirname(scriptPath),
      stdio: ['pipe', 'pipe', 'pipe']
    })

    let stdout = ''
    let stderr = ''

    pythonProcess.stdout.on('data', (data) => {
      stdout += data.toString()
    })

    pythonProcess.stderr.on('data', (data) => {
      stderr += data.toString()
    })

    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        console.error('Python script failed:')
        console.error(stderr)
        reject(new Error(`Combat simulator failed with code ${code}`))
        return
      }

      try {
        // The script saves to 'combat_events.json' by default
        const eventsFile = path.resolve(path.dirname(scriptPath), 'combat_events.json')
        const eventsData = JSON.parse(fs.readFileSync(eventsFile, 'utf-8'))

        // Convert the events to the format expected by the test
        const events: CombatEvent[] = []

        for (const event of eventsData) {
          if (event.type === 'state_snapshot') {
            // State snapshots have game_state directly
            events.push({
              type: 'state_snapshot',
              seq: event.seq || event.data?.seq,
              timestamp: event.timestamp || event.data?.timestamp,
              game_state: event.game_state || event.data
            })
          } else {
            // Other events
            events.push({
              ...event,
              seq: event.seq,
              timestamp: event.timestamp
            })
          }
        }

        resolve(events)
      } catch (e) {
        reject(e)
      }
    })

    pythonProcess.on('error', (err) => {
      reject(err)
    })
  })
}

// Run the event replay test
async function runEventReplayTest(seed?: number) {
  console.log(`Generating events with combat simulator${seed ? ` (seed: ${seed})` : ' (random seed)'}`)

  const events = await generateEventsWithSimulator(seed)
  console.log(`Generated ${events.length} events`)

  let state = createInitialState()
  const context = { overwriteSnapshots: false, simTime: 0 }
  let totalDesyncs = 0

  for (const event of events) {
    // Apply the event to update state
    state = applyCombatEvent(state, event, context)

    // If this is a state_snapshot, compare with authoritative backend state
    if (event.type === 'state_snapshot' && event.game_state) {
      const desyncs = compareCombatStates(state, event.game_state, event)

      if (desyncs.length > 0) {
        console.log(`\n❌ DESYNC DETECTED at seq ${event.seq}, timestamp ${event.timestamp}`)
        for (const desync of desyncs) {
          console.log(`  Unit: ${desync.unit_name} (${desync.unit_id})`)
          for (const [field, values] of Object.entries(desync.diff)) {
            console.log(`    ${field}: UI=${values.ui} vs Server=${values.server}`)
          }
        }
        totalDesyncs += desyncs.length
      } else {
        console.log(`✅ State snapshot ${event.seq} matches (timestamp: ${event.timestamp})`)
      }
    }
  }

  console.log(`\n🎯 Test completed. Total desyncs: ${totalDesyncs}`)

  if (totalDesyncs === 0) {
    console.log('🎉 All state snapshots matched! Frontend logic is correct.')
    process.exit(0)
  } else {
    console.log('💥 Desyncs found! Frontend logic needs fixing.')
    process.exit(1)
  }
}

// Main execution
async function main() {
  const args = process.argv.slice(2)

  let seed: number | undefined

  if (args.length > 0) {
    const seedArg = args[0]
    if (seedArg === '--help' || seedArg === '-h') {
      console.log(`
TypeScript Event Replay Test

Tests the frontend applyEvent logic by generating events with the combat simulator
and comparing reconstructed state with authoritative backend state snapshots.

Usage:
  npx tsx test-event-replay.ts [seed]

Examples:
  npx tsx test-event-replay.ts 5        # Use seed 5
  npx tsx test-event-replay.ts          # Use random seed
  npx tsx test-event-replay.ts --help   # Show this help
`)
      process.exit(0)
    }

    const parsedSeed = parseInt(seedArg)
    if (!isNaN(parsedSeed)) {
      seed = parsedSeed
    }
  }

  try {
    await runEventReplayTest(seed)
  } catch (error) {
    console.error('Test failed:', error)
    process.exit(1)
  }
}

main()