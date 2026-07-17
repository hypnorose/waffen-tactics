import { describe, expect, it } from 'vitest'
import {
  createCombatSummary,
  formatCombatLogEntry,
  getTopDamageDealer,
  updateCombatSummary,
} from '../combatPresentation'
import { CombatEvent } from '../types'

describe('combatPresentation', () => {
  it('formats bonus attacks and updates summary metrics', () => {
    const summary = createCombatSummary()
    const attack: CombatEvent = {
      type: 'unit_attack',
      attacker_id: 'unit_a',
      attacker_name: 'Unit A',
      target_id: 'unit_b',
      target_name: 'Unit B',
      damage: 40,
      applied_damage: 40,
      bonus_attack: true,
      attacker_current_mana: 100,
      attacker_max_mana: 100,
      seq: 12,
      timestamp: 4.2,
    }

    const log = formatCombatLogEntry(attack)
    expect(log).toContain('[BONUS]')
    expect(log).toContain('Unit A -> Unit B')

    const next = updateCombatSummary(summary, attack)
    expect(next.bonusAttacks).toBe(1)
    expect(next.focus?.bonus_attack).toBe(true)
    expect(next.totalDamageByUnit.unit_a.damage).toBe(40)
    expect(getTopDamageDealer(next)).toEqual({
      unit_id: 'unit_a',
      unit_name: 'Unit A',
      damage: 40,
    })
  })

  it('tracks first death and round result text', () => {
    const summary = createCombatSummary()
    const death: CombatEvent = {
      type: 'unit_died',
      unit_id: 'opp_1',
      unit_name: 'Opponent',
      seq: 21,
      timestamp: 6.8,
    }
    const result: CombatEvent = {
      type: 'victory',
      message: 'ZWYCIESTWO',
      seq: 22,
      timestamp: 7.0,
    }

    const afterDeath = updateCombatSummary(summary, death)
    const afterResult = updateCombatSummary(afterDeath, result)

    expect(afterResult.firstDeath?.unit_id).toBe('opp_1')
    expect(afterResult.roundResult).toContain('ZWYCIESTWO')
  })

  it('keeps percentage and flat stat buffs distinct in the combat log', () => {
    expect(formatCombatLogEntry({
      type: 'stat_buff', unit_name: 'Mage', amount: 20, stat: 'attack_speed', value_type: 'percentage',
    })).toContain('+20% attack_speed')
    expect(formatCombatLogEntry({
      type: 'stat_buff', unit_name: 'Tank', amount: 20, stat: 'health', value_type: 'flat',
    })).toContain('+20 health')
  })

  it('calculates average dealt and received damage for participating units', () => {
    const summary = createCombatSummary()
    const events: CombatEvent[] = [
      { type: 'start', timestamp: 0 },
      {
        type: 'unit_attack',
        attacker_id: 'unit_a',
        attacker_name: 'Unit A',
        target_id: 'unit_b',
        target_name: 'Unit B',
        applied_damage: 40,
        timestamp: 1,
      },
      {
        type: 'unit_attack',
        attacker_id: 'unit_b',
        attacker_name: 'Unit B',
        target_id: 'unit_a',
        target_name: 'Unit A',
        applied_damage: 20,
        timestamp: 3,
      },
      { type: 'unit_died', unit_id: 'unit_b', unit_name: 'Unit B', timestamp: 4 },
      { type: 'victory', message: 'ZWYCIESTWO', timestamp: 5 },
    ]

    const result = events.reduce(updateCombatSummary, summary)

    expect(result.unitStatsByUnit.unit_a).toMatchObject({
      participated: true,
      damage_dealt: 40,
      damage_received: 20,
      active_seconds: 4,
      avg_dps: 10,
      avg_damage_received: 5,
    })
    expect(result.unitStatsByUnit.unit_b?.avg_dps).toBeCloseTo(20 / 3, 5)
    expect(result.unitStatsByUnit.unit_b?.avg_damage_received).toBeCloseTo(40 / 3, 5)
  })
})
