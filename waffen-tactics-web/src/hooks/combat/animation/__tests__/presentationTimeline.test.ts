import { describe, expect, it } from 'vitest'
import type { CombatEvent } from '../../types'
import {
  buildPresentationTimeline,
  clearPresentationTracks,
  createPresentationTimeline,
  getActivePresentationTracks,
  getPresentationCoverage,
  pruneExpiredPresentationTracks,
  reducePresentationTimeline,
} from '../presentationTimeline'

function event(overrides: Partial<CombatEvent> = {}): CombatEvent {
  return {
    type: 'unit_attack',
    event_id: 'combat:1',
    seq: 1,
    timestamp: 1,
    ...overrides,
  }
}

describe('presentationTimeline', () => {
  it('creates a melee track from an animation_start event', () => {
    const state = reducePresentationTimeline(createPresentationTimeline(), event({
      type: 'animation_start',
      animation_id: 'basic_attack',
      attacker_id: 'player_0',
      target_id: 'opp_0',
      duration: 0.24,
    }))

    expect(Object.values(state.tracks)).toEqual([
      expect.objectContaining({
        intent: 'melee_lunge',
        unitId: 'player_0',
        targetId: 'opp_0',
        duration: 0.24,
      }),
    ])
    expect(state.diagnostics).toEqual([])
  })

  it('classifies ranged attacks, shield impacts, dodges, and deaths', () => {
    let state = createPresentationTimeline()
    state = reducePresentationTimeline(state, event({
      type: 'animation_start',
      event_id: 'combat:2',
      animation_id: 'ranged_projectile',
      attacker_id: 'player_0',
      target_id: 'opp_0',
      timestamp: 2,
    }))
    state = reducePresentationTimeline(state, event({
      type: 'damage',
      event_id: 'combat:3',
      target_id: 'opp_0',
      shield_absorbed: 10,
      timestamp: 2.1,
    }))
    state = reducePresentationTimeline(state, event({
      type: 'damage_dodged',
      event_id: 'combat:4',
      target_id: 'player_0',
      timestamp: 2.2,
    }))
    state = reducePresentationTimeline(state, event({
      type: 'unit_died',
      event_id: 'combat:5',
      unit_id: 'opp_0',
      timestamp: 2.3,
    }))

    expect(Object.values(state.tracks).map((track) => track.intent)).toEqual([
      'ranged_projectile',
      'shield_hit',
      'dodge',
      'death',
    ])
  })

  it('maps canonical status, multi-hit, and damage-over-time events to explicit tracks', () => {
    let state = createPresentationTimeline()
    const events: CombatEvent[] = [
      event({ type: 'shield_broken', event_id: 'combat:status-1', unit_id: 'opp_0', target_id: 'opp_0', seq: 10 }),
      event({ type: 'unit_stunned', event_id: 'combat:status-2', unit_id: 'opp_0', seq: 11 }),
      event({ type: 'effect_applied', event_id: 'combat:status-3', unit_id: 'opp_0', effect_id: 'slow', seq: 12 }),
      event({ type: 'stat_buff', event_id: 'combat:status-4', unit_id: 'opp_0', item_effect_id: 'item:buff', seq: 13 }),
      event({ type: 'formation_changed', event_id: 'combat:status-5', unit_id: 'opp_0', seq: 14 }),
      event({ type: 'multi_hit', event_id: 'combat:status-6', target_ids: ['opp_0', 'player_0'], seq: 15 }),
      event({ type: 'damage_over_time_applied', event_id: 'combat:status-7', unit_id: 'opp_0', seq: 16 }),
      event({ type: 'damage_over_time_tick', event_id: 'combat:status-8', unit_id: 'opp_0', damage: 3, seq: 17 }),
    ]

    for (const nextEvent of events) state = reducePresentationTimeline(state, nextEvent)

    expect(Object.values(state.tracks).map((track) => track.intent)).toEqual([
      'shield_break',
      'stun',
      'effect',
      'item',
      'formation_change',
      'multi_hit',
      'multi_hit',
      'damage_over_time',
      'target_recoil',
    ])
    expect(state.diagnostics).toEqual([])
  })

  it('distinguishes mapped, deliberately omitted, and unknown presentation event types', () => {
    expect(getPresentationCoverage('unit_stunned')).toBe('mapped')
    expect(getPresentationCoverage('mana_update')).toBe('omitted')
    expect(getPresentationCoverage('future_event')).toBe('unknown')

    const state = reducePresentationTimeline(createPresentationTimeline(), event({ type: 'future_event', event_id: 'combat:unknown' }))
    expect(state.diagnostics).toEqual([
      expect.objectContaining({ code: 'unknown_presentation_event', eventType: 'future_event' }),
    ])
  })

  it('reports missing actor or target ids without creating a track', () => {
    const state = reducePresentationTimeline(createPresentationTimeline(), event({
      type: 'animation_start',
      attacker_id: 'player_0',
      event_id: 'combat:missing-target',
      target_id: undefined,
    }))

    expect(state.tracks).toEqual({})
    expect(state.diagnostics).toEqual([
      expect.objectContaining({ code: 'missing_target', eventType: 'animation_start' }),
    ])
  })

  it('rejects unknown actors after the canonical roster is registered', () => {
    let state = reducePresentationTimeline(createPresentationTimeline(), event({
      type: 'units_init',
      event_id: 'combat:init',
      seq: 1,
      timestamp: 0,
      player_units: [{ id: 'player_0' } as any],
      opponent_units: [{ id: 'opp_0' } as any],
    }))
    state = reducePresentationTimeline(state, event({
      type: 'animation_start',
      event_id: 'combat:unknown-target',
      seq: 2,
      timestamp: 1,
      animation_id: 'basic_attack',
      attacker_id: 'player_0',
      target_id: 'ghost',
    }))

    expect(state.tracks).toEqual({})
    expect(state.diagnostics).toEqual([
      expect.objectContaining({
        code: 'missing_target',
        eventId: 'combat:unknown-target',
        seq: 2,
        unitId: 'ghost',
      }),
    ])
  })

  it('rebuilds only through the requested replay index and exposes active tracks', () => {
    const events = [
      event({ type: 'animation_start', event_id: 'combat:10', animation_id: 'basic_attack', attacker_id: 'player_0', target_id: 'opp_0', timestamp: 1 }),
      event({ type: 'unit_died', event_id: 'combat:11', unit_id: 'opp_0', timestamp: 2 }),
    ]

    const beforeDeath = buildPresentationTimeline(events, 0)
    expect(Object.values(beforeDeath.tracks).map((track) => track.intent)).toEqual(['melee_lunge'])
    expect(getActivePresentationTracks(beforeDeath, 1.1)).toHaveLength(1)
    expect(getActivePresentationTracks(beforeDeath, 1.5)).toHaveLength(0)
  })

  it('prunes expired live tracks without removing diagnostics', () => {
    let state = createPresentationTimeline()
    state = reducePresentationTimeline(state, event({
      type: 'animation_start',
      event_id: 'combat:expired',
      animation_id: 'basic_attack',
      attacker_id: 'player_0',
      target_id: 'opp_0',
      timestamp: 1,
      duration: 0.1,
    }))
    state = reducePresentationTimeline(state, event({
      type: 'future_event',
      event_id: 'combat:diagnostic',
      timestamp: 3,
    }))
    state = reducePresentationTimeline(state, event({
      type: 'animation_start',
      event_id: 'combat:future',
      animation_id: 'basic_attack',
      attacker_id: 'player_0',
      target_id: 'opp_0',
      timestamp: 2.5,
      duration: 0.2,
    }))

    const pruned = pruneExpiredPresentationTracks(state, 2)
    expect(Object.values(pruned.tracks)).toEqual([
      expect.objectContaining({ sourceEventId: 'combat:future' }),
    ])
    expect(pruned.diagnostics).toHaveLength(1)
    expect(clearPresentationTracks(state).diagnostics).toEqual(state.diagnostics)
  })
})
