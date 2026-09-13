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

  it('deduplicates repeated animation starts for the same attack window', () => {
    let state = createPresentationTimeline()
    state = reducePresentationTimeline(state, event({
      type: 'animation_start',
      event_id: 'combat:duplicate-animation-1',
      seq: 10,
      timestamp: 4,
      animation_id: 'basic_attack',
      attacker_id: 'player_0',
      target_id: 'opp_0',
    }))
    state = reducePresentationTimeline(state, event({
      type: 'animation_start',
      event_id: 'combat:duplicate-animation-2',
      seq: 11,
      timestamp: 4.04,
      animation_id: 'basic_attack',
      attacker_id: 'player_0',
      target_id: 'opp_0',
    }))

    expect(Object.values(state.tracks)).toHaveLength(1)
    expect(Object.values(state.tracks)[0]).toEqual(expect.objectContaining({
      sourceEventId: 'combat:duplicate-animation-1',
      intent: 'melee_lunge',
    }))
  })

  it('coalesces alias impact events and promotes a plain recoil to a shield hit', () => {
    let state = createPresentationTimeline()
    state = reducePresentationTimeline(state, event({
      type: 'unit_attack',
      event_id: 'combat:alias-unit-attack',
      seq: 20,
      timestamp: 5,
      attacker_id: 'player_0',
      target_id: 'opp_0',
      shield_absorbed: 0,
    }))
    state = reducePresentationTimeline(state, event({
      type: 'damage',
      event_id: 'combat:alias-damage',
      seq: 21,
      timestamp: 5.04,
      attacker_id: 'player_0',
      target_id: 'opp_0',
      shield_absorbed: 8,
    }))

    const tracks = Object.values(state.tracks)
    expect(tracks).toHaveLength(1)
    expect(tracks[0]).toEqual(expect.objectContaining({
      sourceEventId: 'combat:alias-unit-attack',
      intent: 'shield_hit',
      targetId: 'opp_0',
      unitId: 'player_0',
    }))
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
      attacker_id: 'player_0',
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
    expect(Object.values(state.tracks).find((track) => track.intent === 'shield_hit')).toEqual(expect.objectContaining({
      unitId: 'player_0',
      targetId: 'opp_0',
    }))
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

  it.each([
    ['animation_start', { animation_id: 'basic_attack', attacker_id: 'player_0', target_id: 'opp_0' }, 'melee_lunge'],
    ['attack', { attacker_id: 'player_0', target_id: 'opp_0' }, 'target_recoil'],
    ['unit_attack', { attacker_id: 'player_0', target_id: 'opp_0' }, 'target_recoil'],
    ['damage', { attacker_id: 'player_0', target_id: 'opp_0' }, 'target_recoil'],
    ['damage_dodged', { attacker_id: 'player_0', target_id: 'opp_0' }, 'dodge'],
    ['attack_missed', { attacker_id: 'player_0', target_id: 'opp_0' }, 'dodge'],
    ['miss', { attacker_id: 'player_0', target_id: 'opp_0' }, 'dodge'],
    ['multi_hit', { attacker_id: 'player_0', target_ids: ['opp_0'] }, 'multi_hit'],
    ['unit_died', { unit_id: 'opp_0' }, 'death'],
    ['unit_revived', { unit_id: 'opp_0' }, 'revive'],
    ['revive', { unit_id: 'opp_0' }, 'revive'],
    ['shield_applied', { unit_id: 'opp_0' }, 'shield'],
    ['shield_broken', { unit_id: 'opp_0' }, 'shield_break'],
    ['damage_over_time_applied', { unit_id: 'opp_0' }, 'damage_over_time'],
    ['damage_over_time_tick', { unit_id: 'opp_0' }, 'target_recoil'],
    ['damage_over_time_expired', { unit_id: 'opp_0' }, 'damage_over_time'],
    ['effect_applied', { unit_id: 'opp_0' }, 'effect'],
    ['effect_expired', { unit_id: 'opp_0' }, 'effect'],
    ['stat_buff', { unit_id: 'opp_0' }, 'buff'],
    ['passive_triggered', { unit_id: 'opp_0' }, 'passive'],
    ['unit_stunned', { unit_id: 'opp_0' }, 'stun'],
    ['unit_heal', { unit_id: 'opp_0' }, 'heal'],
    ['heal', { unit_id: 'opp_0' }, 'heal'],
    ['hp_regen', { unit_id: 'opp_0' }, 'heal'],
    ['regen_gain', { unit_id: 'opp_0' }, 'heal'],
    ['formation_changed', { unit_id: 'opp_0' }, 'formation_change'],
  ] as const)('maps canonical %s to one presentation intent', (type, fields, intent) => {
    const state = reducePresentationTimeline(createPresentationTimeline(), event({
      ...fields,
      type,
      event_id: `combat:mapped:${type}`,
      seq: 2,
      timestamp: 1,
    }))

    expect(state.diagnostics).toEqual([])
    expect(Object.values(state.tracks).map((track) => track.intent)).toEqual([intent])
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

  it('does not infer a single-target presentation target from unit_id', () => {
    let state = reducePresentationTimeline(createPresentationTimeline(), event({
      type: 'units_init',
      event_id: 'combat:strict-target-init',
      seq: 1,
      timestamp: 0,
      player_units: [{ id: 'player_0' } as any],
      opponent_units: [{ id: 'opp_0' } as any],
    }))

    for (const [index, type] of (['unit_attack', 'damage', 'damage_dodged', 'multi_hit'] as const).entries()) {
      state = reducePresentationTimeline(state, event({
        type,
        event_id: `combat:strict-target-${type}`,
        seq: index + 2,
        timestamp: index + 1,
        unit_id: 'opp_0',
        attacker_id: 'player_0',
        target_id: undefined,
      }))
    }

    expect(state.tracks).toEqual({})
    expect(state.diagnostics).toEqual([
      expect.objectContaining({ code: 'missing_target', eventType: 'unit_attack', unitId: undefined }),
      expect.objectContaining({ code: 'missing_target', eventType: 'damage', unitId: undefined }),
      expect.objectContaining({ code: 'missing_target', eventType: 'damage_dodged', unitId: undefined }),
      expect.objectContaining({ code: 'missing_target', eventType: 'multi_hit' }),
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

  it('treats an explicitly empty canonical roster as ready and rejects visual actors', () => {
    let state = reducePresentationTimeline(createPresentationTimeline(), event({
      type: 'units_init',
      event_id: 'combat:empty-init',
      seq: 1,
      timestamp: 0,
      player_units: [],
      opponent_units: [],
    }))
    state = reducePresentationTimeline(state, event({
      type: 'unit_died',
      event_id: 'combat:empty-roster-death',
      seq: 2,
      timestamp: 1,
      unit_id: 'ghost',
    }))

    expect(state.actorRegistryReady).toBe(true)
    expect(state.tracks).toEqual({})
    expect(state.diagnostics).toEqual([
      expect.objectContaining({
        code: 'missing_actor',
        eventId: 'combat:empty-roster-death',
        seq: 2,
        unitId: 'ghost',
      }),
    ])
  })

  it('rejects presentation events after death until a canonical revive', () => {
    let state = reducePresentationTimeline(createPresentationTimeline(), event({
      type: 'units_init',
      event_id: 'combat:lifecycle-init',
      seq: 1,
      timestamp: 0,
      player_units: [{ id: 'player_0' } as any],
      opponent_units: [{ id: 'opp_0' } as any],
    }))
    state = reducePresentationTimeline(state, event({
      type: 'unit_died',
      event_id: 'combat:lifecycle-death',
      seq: 2,
      timestamp: 1,
      unit_id: 'opp_0',
    }))
    state = reducePresentationTimeline(state, event({
      type: 'unit_attack',
      event_id: 'combat:lifecycle-after-death',
      seq: 3,
      timestamp: 2,
      target_id: 'opp_0',
    }))

    expect(state.deadActors).toEqual({ opp_0: true })
    expect(Object.values(state.tracks).map((track) => track.intent)).toEqual(['death'])
    expect(state.diagnostics).toEqual([
      expect.objectContaining({
        code: 'dead_actor',
        eventId: 'combat:lifecycle-after-death',
        seq: 3,
        unitId: 'opp_0',
      }),
    ])

    state = reducePresentationTimeline(state, event({
      type: 'unit_revived',
      event_id: 'combat:lifecycle-revive',
      seq: 4,
      timestamp: 3,
      unit_id: 'opp_0',
      cause: 'set2_revive',
      pre_hp: 0,
      post_hp: 300,
      max_hp: 600,
      effect_id: 'set2:opp_0:revive-untargetable',
      effect: {
        id: 'set2:opp_0:revive-untargetable',
        type: 'untargetable',
        duration: 0.75,
        expires_at: 3.75,
      },
      protection: {
        effect_id: 'set2:opp_0:revive-untargetable',
        type: 'untargetable',
        duration: 0.75,
        expires_at: 3.75,
      },
    }))
    state = reducePresentationTimeline(state, event({
      type: 'unit_attack',
      event_id: 'combat:lifecycle-after-revive',
      seq: 5,
      timestamp: 4,
      target_id: 'opp_0',
    }))

    expect(state.deadActors).toEqual({})
    expect(Object.values(state.tracks).map((track) => track.intent)).toEqual(['death', 'revive', 'target_recoil'])
  })

  it('accepts an explicit delayed damage_dodged cancellation after target death', () => {
    let state = reducePresentationTimeline(createPresentationTimeline(), event({
      type: 'units_init',
      event_id: 'combat:cancelled-init',
      seq: 1,
      timestamp: 0,
      player_units: [{ id: 'player_0' } as any],
      opponent_units: [{ id: 'opp_2' } as any],
    }))
    state = reducePresentationTimeline(state, event({
      type: 'unit_died',
      event_id: 'combat:cancelled-death',
      seq: 2,
      timestamp: 1,
      unit_id: 'opp_2',
    }))
    state = reducePresentationTimeline(state, event({
      type: 'damage_dodged',
      event_id: 'a6ef77ffd662f91770d6074d0780e846:1247',
      seq: 1246,
      timestamp: 2,
      attacker_id: 'player_0',
      target_id: 'opp_2',
      cancelled: true,
      cause: 'target_dead_before_impact',
    }))

    expect(state.diagnostics).toEqual([])
    expect(Object.values(state.tracks).map((track) => track.intent)).toEqual(['death'])
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

  it('orders concurrent tracks by explicit intensity rank before stable id', () => {
    let state = createPresentationTimeline()
    state = reducePresentationTimeline(state, event({
      type: 'effect_applied',
      event_id: 'combat:rank-small',
      unit_id: 'opp_0',
      timestamp: 1,
    }))
    state = reducePresentationTimeline(state, event({
      type: 'damage',
      event_id: 'combat:rank-medium',
      attacker_id: 'player_0',
      target_id: 'opp_0',
      timestamp: 1,
    }))
    state = reducePresentationTimeline(state, event({
      type: 'animation_start',
      event_id: 'combat:rank-large',
      animation_id: 'basic_attack',
      attacker_id: 'player_0',
      target_id: 'opp_0',
      bonus_attack: true,
      timestamp: 1,
    }))

    expect(getActivePresentationTracks(state, 1.05).map((track) => track.sourceEventId)).toEqual([
      'combat:rank-large',
      'combat:rank-medium',
      'combat:rank-small',
    ])
  })

  it('keeps overlapping attack, impact, and status tracks active in deterministic order', () => {
    let state = createPresentationTimeline()
    state = reducePresentationTimeline(state, event({
      type: 'animation_start',
      event_id: 'combat:concurrent-attack',
      animation_id: 'basic_attack',
      attacker_id: 'player_0',
      target_id: 'opp_0',
      timestamp: 1,
      duration: 0.5,
    }))
    state = reducePresentationTimeline(state, event({
      type: 'damage',
      event_id: 'combat:concurrent-impact',
      attacker_id: 'player_0',
      target_id: 'opp_0',
      timestamp: 1.05,
    }))
    state = reducePresentationTimeline(state, event({
      type: 'unit_stunned',
      event_id: 'combat:concurrent-status',
      unit_id: 'opp_0',
      timestamp: 1.1,
    }))

    const active = getActivePresentationTracks(state, 1.15)

    expect(active.map((track) => track.sourceEventId)).toEqual([
      'combat:concurrent-attack',
      'combat:concurrent-impact',
      'combat:concurrent-status',
    ])
    expect(active.map((track) => track.intent)).toEqual([
      'melee_lunge',
      'target_recoil',
      'stun',
    ])
    expect(getActivePresentationTracks(state, 1.4).map((track) => track.sourceEventId)).toEqual([
      'combat:concurrent-attack',
    ])
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
