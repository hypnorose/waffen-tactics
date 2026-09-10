import { describe, expect, it } from 'vitest'
import {
  createCombatSummary,
  formatCombatLogEntry,
  getTopDamageDealer,
  updateCombatSummary,
} from '../combatPresentation'
import { CombatEvent } from '../types'

describe('combatPresentation', () => {
  it('includes the passive display name in passive activation logs', () => {
    expect(formatCombatLogEntry({
      type: 'passive_triggered',
      unit_name: 'Fiko',
      passive_name: 'Jajcarz',
      description: 'Ogłusza po bonus attacku.',
    })).toBe('[PASSIVE] Fiko — Jajcarz: Ogłusza po bonus attacku.')
  })

  it('keeps passive trigger and target metadata visible in the shared log', () => {
    const log = formatCombatLogEntry({
      type: 'passive_triggered',
      unit_name: 'Fiko',
      description: 'Pasywka aktywna',
      trigger: 'on_attack_count',
      target: 'enemy',
      target_id: 'opp_0',
      target_name: 'Goblin',
      scope: 'team',
      limit: 1,
      duration: 3,
    })

    expect(log).toContain('trigger: on_attack_count')
    expect(log).toContain('cel: Goblin')
    expect(log).toContain('typ celu: enemy')
    expect(log).toContain('zakres: team')
    expect(log).toContain('limit: 1')
    expect(log).toContain('czas: 3s')
  })

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

  it('formats skill casts with the canonical caster, target, and damage', () => {
    expect(formatCombatLogEntry({
      type: 'skill_cast',
      caster_id: 'mage',
      caster_name: 'Mage',
      skill_name: 'Arcane Bolt',
      target_id: 'goblin',
      target_name: 'Goblin',
      damage: 42,
    })).toBe('[SKILL] Mage używa Arcane Bolt na Goblin za 42 obrażeń')
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

  it('does not render continuous mana updates in the player-facing combat log', () => {
    expect(formatCombatLogEntry({
      type: 'mana_update',
      unit_name: 'Mage',
      current_mana: 80,
      max_mana: 100,
    })).toBeNull()
  })

  it('keeps canonical effect context visible in the shared live/replay log formatter', () => {
    const log = formatCombatLogEntry({
      type: 'stat_buff',
      unit_name: 'Tank',
      caster_name: 'Support',
      amount: 20,
      stat: 'defense',
      duration: 3,
      cause: 'on_enemy_death',
      scope: 'team',
      limit: 1,
    })

    expect(log).toContain('źródło: Support')
    expect(log).toContain('powód: on_enemy_death')
    expect(log).toContain('zakres: team')
    expect(log).toContain('limit: 1')
    expect(log).toContain('for 3s')
  })

  it('shows effect description and expiry metadata when canonical fields are present', () => {
    const log = formatCombatLogEntry({
      type: 'effect_applied',
      unit_name: 'Target',
      caster_name: 'Caster',
      effect_type: 'stun',
      description: 'Ogłuszenie z pasywki',
      expires_at: 7.5,
    })

    expect(log).toContain('źródło: Caster')
    expect(log).toContain('wygasa: 7.50s')
    expect(log).toContain('Ogłuszenie z pasywki')
  })

  it('does not present fully shield-absorbed DoT as HP loss', () => {
    const event: CombatEvent = {
      type: 'damage_over_time_tick',
      unit_id: 'unit_b',
      unit_name: 'Unit B',
      damage: 8,
      pre_hp: 100,
      post_hp: 100,
      shield_absorbed: 8,
    }

    expect(formatCombatLogEntry(event)).toBe('[DOT] Unit B -8 shield')
    const result = updateCombatSummary(createCombatSummary(), event)
    expect(result.unitStatsByUnit.unit_b.damage_received).toBe(0)
  })

  it('separates HP and shield loss for partially absorbed DoT', () => {
    const event: CombatEvent = {
      type: 'damage_over_time_tick',
      unit_id: 'unit_b',
      unit_name: 'Unit B',
      damage: 8,
      pre_hp: 100,
      post_hp: 95,
      shield_absorbed: 3,
    }

    expect(formatCombatLogEntry(event)).toBe('[DOT] Unit B -5 HP, -3 shield')
    const result = updateCombatSummary(createCombatSummary(), event)
    expect(result.unitStatsByUnit.unit_b.damage_received).toBe(5)
  })

  it('keeps no-shield DoT presentation and metrics as HP damage', () => {
    const event: CombatEvent = {
      type: 'damage_over_time_tick',
      unit_id: 'unit_b',
      unit_name: 'Unit B',
      damage: 8,
      pre_hp: 100,
      post_hp: 92,
      shield_absorbed: 0,
    }

    expect(formatCombatLogEntry(event)).toBe('[DOT] Unit B -8 HP')
    const result = updateCombatSummary(createCombatSummary(), event)
    expect(result.unitStatsByUnit.unit_b.damage_received).toBe(8)
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
