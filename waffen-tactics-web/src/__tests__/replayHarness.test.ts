import { describe, expect, it } from 'vitest'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { spawnSync } from 'node:child_process'

const harness = path.resolve(__dirname, '../../test-event-replay.mjs')
const diagnosticFixture = path.resolve(__dirname, '../../test-fixtures/desync_inspector_export.json')

function runHarness(filePath: string) {
  return spawnSync(process.execPath, [harness, filePath], {
    cwd: path.dirname(harness),
    encoding: 'utf8'
  })
}

function canonicalRegenEvents() {
  const unit = {
    id: 'opp_0',
    name: 'Test Opponent',
    hp: 100,
    max_hp: 100,
    attack: 10,
    defense: 5,
    attack_speed: 1,
    star_level: 1,
    position: 'front',
    effects: [],
    current_mana: 0,
    max_mana: 100,
    shield: 0,
    buffed_stats: {
      hp: 100,
      attack: 10,
      defense: 5,
      attack_speed: 1,
      max_mana: 100,
      hp_regen_per_sec: 0
    }
  }
  return [
    { type: 'units_init', seq: 1, player_units: [], opponent_units: [unit] },
    {
      type: 'regen_gain',
      seq: 2,
      timestamp: 1,
      unit_id: 'opp_0',
      unit_name: 'Test Opponent',
      amount_per_sec: 6,
      total_amount: 30,
      duration: 5,
      post_hp_regen_per_sec: 6,
      game_state: {
        player_units: [],
        opponent_units: [{ ...unit, buffed_stats: { ...unit.buffed_stats, hp_regen_per_sec: 6 } }]
      }
    }
  ]
}

describe('standalone replay CLI input contract', () => {
  it('rejects a DesyncInspector diagnostic export instead of reporting success', () => {
    const result = runHarness(diagnosticFixture)

    expect(result.status).not.toBe(0)
    expect(`${result.stdout}\n${result.stderr}`).toContain('DesyncInspector diagnostic export')
  })

  it.each(['array', 'jsonl'] as const)('validates canonical %s replay input', (format) => {
    const tempRoot = mkdtempSync(path.join(tmpdir(), 'wft-replay-'))
    try {
      const events = canonicalRegenEvents()
      const content = format === 'array'
        ? JSON.stringify(events)
        : events.map(event => JSON.stringify(event)).join('\n')
      const eventFile = path.join(tempRoot, `${format}.json`)
      writeFileSync(eventFile, content, 'utf8')

      const result = runHarness(eventFile)

      expect(result.status).toBe(0)
      expect(`${result.stdout}\n${result.stderr}`).toContain('SUCCESS: No desyncs detected!')
    } finally {
      rmSync(tempRoot, { recursive: true, force: true })
    }
  })

  it('rejects a canonical event record without type', () => {
    const tempRoot = mkdtempSync(path.join(tmpdir(), 'wft-replay-'))
    try {
      const eventFile = path.join(tempRoot, 'missing-type.json')
      writeFileSync(eventFile, JSON.stringify([{ seq: 1, game_state: {} }]), 'utf8')

      const result = runHarness(eventFile)

      expect(result.status).not.toBe(0)
      expect(`${result.stdout}\n${result.stderr}`).toContain('missing required type field')
    } finally {
      rmSync(tempRoot, { recursive: true, force: true })
    }
  })
})
