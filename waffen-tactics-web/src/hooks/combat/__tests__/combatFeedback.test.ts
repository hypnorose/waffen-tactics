import { describe, expect, it } from 'vitest'
import { getCombatFeedback } from '../combatFeedback'
import type { CombatEvent } from '../types'

describe('getCombatFeedback', () => {
  it('uses canonical HP and shield deltas for damage', () => {
    const feedback = getCombatFeedback({
      type: 'unit_attack',
      event_id: 'combat:10',
      seq: 10,
      target_id: 'opp_0',
      pre_hp: 100,
      post_hp: 72,
      applied_damage: 40,
      shield_absorbed: 12,
    })

    expect(feedback.map(({ text, targetId, tone }) => ({ text, targetId, tone }))).toEqual([
      { text: '-28 HP', targetId: 'opp_0', tone: 'damage' },
      { text: '-12 SHIELD', targetId: 'opp_0', tone: 'damage' },
    ])
  })

  it('does not invent HP loss when canonical damage was fully absorbed by shield', () => {
    expect(getCombatFeedback({
      type: 'damage_over_time_tick',
      event_id: 'combat:11',
      unit_id: 'opp_0',
      pre_hp: 100,
      post_hp: 100,
      applied_damage: 20,
      shield_absorbed: 20,
    }).map(({ text }) => text)).toEqual(['-20 SHIELD'])
  })

  it('renders dodges and canonical heal gains distinctly', () => {
    expect(getCombatFeedback({
      type: 'damage_dodged',
      event_id: 'combat:12',
      target_id: 'opp_0',
      dodged: true,
    })[0].text).toBe('DODGE')
    expect(getCombatFeedback({
      type: 'unit_heal',
      event_id: 'combat:13',
      unit_id: 'player_0',
      pre_hp: 40,
      post_hp: 55,
      amount: 30,
    })[0].text).toBe('+15 HP')
  })

  it('marks effect application and expiration without choosing an implicit target', () => {
    expect(getCombatFeedback({ type: 'effect_applied', event_id: 'combat:14', unit_id: 'player_0' })[0].text).toBe('+EFFECT')
    expect(getCombatFeedback({ type: 'effect_expired', event_id: 'combat:15', unit_id: 'player_0', item_id: 'item-1' })[0].text).toBe('-ITEM')
    expect(getCombatFeedback({ type: 'unit_attack', event_id: 'combat:16', unit_id: 'opp_0', damage: 20 })).toEqual([])
  })

  it('renders one deterministic impact per explicit multi-hit target', () => {
    const feedback = getCombatFeedback({
      type: 'multi_hit',
      event_id: 'combat:multi-hit',
      target_ids: ['opp_0', 'player_0'],
      pre_hp: 100,
      post_hp: 88,
      damage: 12,
    })

    expect(feedback.map(({ targetId, text }) => ({ targetId, text }))).toEqual([
      { targetId: 'opp_0', text: 'MULTI-HIT -12 HP' },
      { targetId: 'player_0', text: 'MULTI-HIT -12 HP' },
    ])
    expect(new Set(feedback.map(({ id }) => id)).size).toBe(2)
  })

  it('keeps IDs deterministic for the same canonical event', () => {
    const event: CombatEvent = {
      type: 'stat_buff',
      event_id: 'combat:17',
      seq: 17,
      unit_id: 'player_0',
      stat: 'attack_speed',
      applied_delta: 2.5,
    }
    expect(getCombatFeedback(event)).toEqual(getCombatFeedback(event))
    expect(getCombatFeedback(event)[0].id).toBe('combat-feedback:combat:17:stat')
  })
})
