import { describe, expect, it } from 'vitest'
import type { CombatEvent } from '../../types'
import {
  buildPresentationTimeline,
  createPresentationTimeline,
  getActivePresentationTracks,
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
})
