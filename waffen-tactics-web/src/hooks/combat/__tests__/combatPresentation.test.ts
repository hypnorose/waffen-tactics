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
})
