import type { CombatEvent } from '../types'
import { isRangedCombatAnimation } from '../combatPresentation'

export type PresentationIntent =
  | 'melee_lunge'
  | 'ranged_projectile'
  | 'target_recoil'
  | 'shield_hit'
  | 'shield_break'
  | 'multi_hit'
  | 'dodge'
  | 'death'
  | 'buff'
  | 'heal'
  | 'shield'
  | 'effect'
  | 'passive'
  | 'item'
  | 'stun'
  | 'formation_change'
  | 'damage_over_time'
  | 'revive'

export type PresentationIntensity = 'small' | 'medium' | 'large'

export interface PresentationTrack {
  id: string
  intent: PresentationIntent
  unitId?: string
  targetId?: string
  sourceSeq?: number
  sourceEventId?: string
  startedAt: number
  duration: number
  intensity: PresentationIntensity
}

export interface PresentationDiagnostic {
  code: 'missing_actor' | 'missing_target' | 'dead_actor' | 'invalid_animation' | 'unknown_presentation_event'
  message: string
  eventType: string
  eventId?: string
  seq?: number
  unitId?: string
}

export interface PresentationTimelineState {
  tracks: Record<string, PresentationTrack>
  diagnostics: PresentationDiagnostic[]
  /** Logical actor registry populated by the canonical units_init event. */
  actors: Record<string, true>
  /** Distinguishes a canonical empty roster from synthetic fixtures without units_init. */
  actorRegistryReady: boolean
  /** Lifecycle state is presentation metadata only; combat HP remains reducer-owned. */
  deadActors: Record<string, true>
}

export const createPresentationTimeline = (): PresentationTimelineState => ({
  tracks: {},
  diagnostics: [],
  actors: {},
  actorRegistryReady: false,
  deadActors: {},
})

/**
 * Removes transient tracks that have already finished in simulation time.
 * Historical replay rebuilds intentionally start from a fresh timeline, so
 * pruning the live projection cannot change authoritative combat state.
 */
export function pruneExpiredPresentationTracks(
  state: PresentationTimelineState,
  currentTime: number,
): PresentationTimelineState {
  if (!Number.isFinite(currentTime)) return state

  const activeEntries = Object.entries(state.tracks).filter(([, track]) => (
    currentTime <= track.startedAt + track.duration
  ))
  if (activeEntries.length === Object.keys(state.tracks).length) return state

  return {
    ...state,
    tracks: Object.fromEntries(activeEntries),
  }
}

/** Clears transient VFX tracks while preserving replay diagnostics. */
export function clearPresentationTracks(
  state: PresentationTimelineState,
): PresentationTimelineState {
  if (Object.keys(state.tracks).length === 0) return state
  return { ...state, tracks: {} }
}

function registerActorsFromInit(
  state: PresentationTimelineState,
  event: CombatEvent,
): PresentationTimelineState {
  if (event.type !== 'units_init') return state

  const actorIds = [
    ...(Array.isArray(event.player_units) ? event.player_units : []),
    ...(Array.isArray(event.opponent_units) ? event.opponent_units : []),
  ]
    .map((unit) => unit?.id)
    .filter((id): id is string => typeof id === 'string' && id.trim() !== '')

  return {
    ...state,
    actors: actorIds.reduce<Record<string, true>>((actors, id) => {
      actors[id] = true
      return actors
    }, { ...state.actors }),
    actorRegistryReady: true,
  }
}

function isKnownActor(state: PresentationTimelineState, unitId: string): boolean {
  // Synthetic timeline tests may intentionally omit units_init. In a real
  // canonical stream the registry is populated before visual events arrive.
  return !state.actorRegistryReady || state.actors[unitId] === true
}

function isLiveActor(state: PresentationTimelineState, unitId: string): boolean {
  return !state.deadActors[unitId]
}

const DEFAULT_DURATION_SECONDS = 0.18
const DEFAULT_LUNGE_DURATION_SECONDS = 0.2
const PRESENTATION_INTENSITY_RANK: Record<PresentationIntensity, number> = {
  small: 0,
  medium: 1,
  large: 2,
}

function compareStableIds(left: string, right: string): number {
  if (left === right) return 0
  return left < right ? -1 : 1
}

function eventTime(event: CombatEvent): number {
  return typeof event.timestamp === 'number' && Number.isFinite(event.timestamp)
    ? event.timestamp
    : 0
}

function positiveDuration(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0
    ? Math.min(1.5, Math.max(0.05, value))
    : fallback
}

function eventKey(event: CombatEvent): string {
  return event.event_id || `${event.type}:${event.seq ?? 'na'}:${event.attacker_id || event.unit_id || 'na'}:${event.target_id || ''}`
}

function addTrack(
  state: PresentationTimelineState,
  event: CombatEvent,
  intent: PresentationIntent,
  options: {
    unitId?: string
    targetId?: string
    duration?: number
    intensity?: PresentationIntensity
    role: string
  },
): PresentationTimelineState {
  const id = `${eventKey(event)}:${options.role}`
  if (state.tracks[id]) return state

  return {
    ...state,
    tracks: {
      ...state.tracks,
      [id]: {
        id,
        intent,
        unitId: options.unitId,
        targetId: options.targetId,
        sourceSeq: event.seq,
        sourceEventId: event.event_id,
        startedAt: eventTime(event),
        duration: positiveDuration(options.duration, DEFAULT_DURATION_SECONDS),
        intensity: options.intensity || 'medium',
      },
    },
  }
}

function addDiagnostic(
  state: PresentationTimelineState,
  event: CombatEvent,
  diagnostic: Omit<PresentationDiagnostic, 'eventType' | 'eventId' | 'seq'>,
): PresentationTimelineState {
  const id = `${eventKey(event)}:${diagnostic.code}:${diagnostic.unitId || ''}`
  if (state.diagnostics.some((entry) => `${entry.eventId || eventKey(event)}:${entry.code}:${entry.unitId || ''}` === id)) {
    return state
  }

  return {
    ...state,
    diagnostics: [
      ...state.diagnostics,
      {
        ...diagnostic,
        eventType: event.type,
        eventId: event.event_id,
        seq: event.seq,
      },
    ].slice(-50),
  }
}

function unitRequiredDiagnostic(
  state: PresentationTimelineState,
  event: CombatEvent,
  unitId: string | undefined,
  role: 'attacker' | 'target' | 'unit',
): PresentationTimelineState {
  const code = role === 'target' ? 'missing_target' : 'missing_actor'
  if (unitId && isKnownActor(state, unitId)) return state
  const reason = unitId ? `has no registered ${role} actor` : `is missing its ${role} id`
  return addDiagnostic(state, event, {
    code,
    unitId,
    message: `Presentation event ${event.type} seq=${event.seq ?? 'n/a'} event_id=${event.event_id ?? 'n/a'} ${reason}.`,
  })
}

function liveActorDiagnostic(
  state: PresentationTimelineState,
  event: CombatEvent,
  unitId: string | undefined,
  role: 'attacker' | 'target' | 'unit',
): PresentationTimelineState {
  const next = unitRequiredDiagnostic(state, event, unitId, role)
  if (!unitId || !isKnownActor(next, unitId) || isLiveActor(next, unitId)) return next

  return addDiagnostic(next, event, {
    code: 'dead_actor',
    unitId,
    message: `Presentation event ${event.type} seq=${event.seq ?? 'n/a'} event_id=${event.event_id ?? 'n/a'} references dead ${role} actor ${unitId}.`,
  })
}

function animationContractDiagnostic(
  state: PresentationTimelineState,
  event: CombatEvent,
): PresentationTimelineState {
  const missing: string[] = []
  if (typeof event.animation_id !== 'string' || !event.animation_id.trim()) missing.push('animation_id')
  if (typeof event.event_id !== 'string' || !event.event_id.trim()) missing.push('event_id')
  if (!Number.isInteger(event.seq) || (event.seq || 0) <= 0) missing.push('seq')
  if (typeof event.timestamp !== 'number' || !Number.isFinite(event.timestamp)) missing.push('timestamp')
  if (missing.length === 0) return state

  return addDiagnostic(state, event, {
    code: 'invalid_animation',
    message: `Presentation event ${event.type} seq=${event.seq ?? 'n/a'} event_id=${event.event_id ?? 'n/a'} is missing or has invalid canonical field(s): ${missing.join(', ')}.`,
  })
}

function impactIntensity(event: CombatEvent): PresentationIntensity {
  if (event.bonus_attack) return 'large'
  const damage = Number(event.applied_damage ?? event.damage ?? 0)
  if (Number.isFinite(damage) && damage >= 100) return 'large'
  return 'medium'
}

const PRESENTATION_OMISSION_TYPES = new Set([
  'error',
  'start',
  'units_init',
  'victory',
  'defeat',
  'gold_income',
  'gold_reward',
  'end',
  'state_snapshot',
  'mana_update',
  // skill_cast is replay metadata; animation_start owns its visual track.
  'skill_cast',
])

export type PresentationCoverage = 'mapped' | 'omitted' | 'unknown'

const PRESENTATION_MAPPED_TYPES = new Set([
  'animation_start',
  'attack',
  'unit_attack',
  'damage',
  'damage_dodged',
  'attack_missed',
  'miss',
  'multi_hit',
  'unit_died',
  'unit_revived',
  'revive',
  'shield_applied',
  'shield_broken',
  'damage_over_time_applied',
  'damage_over_time_tick',
  'damage_over_time_expired',
  'effect_applied',
  'effect_expired',
  'stat_buff',
  'passive_triggered',
  'unit_stunned',
  'unit_heal',
  'heal',
  'hp_regen',
  'regen_gain',
  'formation_changed',
])

/** Returns the explicit presentation contract for a canonical event type. */
export function getPresentationCoverage(eventType: string): PresentationCoverage {
  if (PRESENTATION_MAPPED_TYPES.has(eventType)) return 'mapped'
  if (PRESENTATION_OMISSION_TYPES.has(eventType)) return 'omitted'
  return 'unknown'
}

function hasItemContext(event: CombatEvent): boolean {
  return typeof event.item_id === 'string' || typeof event.item_effect_id === 'string'
}

function addTargetImpact(
  state: PresentationTimelineState,
  event: CombatEvent,
  targetId: string,
  intent: 'target_recoil' | 'shield_hit' | 'shield_break' | 'multi_hit' | 'dodge',
  role: string,
  sourceId?: string,
): PresentationTimelineState {
  const next = liveActorDiagnostic(state, event, targetId, 'target')
  if (!isKnownActor(next, targetId) || !isLiveActor(next, targetId)) return next
  return addTrack(next, event, intent, {
    unitId: sourceId,
    targetId,
    duration: intent === 'shield_break' ? 0.2 : 0.16,
    intensity: impactIntensity(event),
    role,
  })
}

function addUnitStatus(
  state: PresentationTimelineState,
  event: CombatEvent,
  intent: Extract<PresentationIntent, 'buff' | 'heal' | 'shield' | 'effect' | 'passive' | 'item' | 'stun' | 'formation_change' | 'damage_over_time'>,
  duration = 0.22,
): PresentationTimelineState {
  const unitId = event.unit_id || event.caster_id
  let next = liveActorDiagnostic(state, event, unitId, 'unit')
  if (!unitId || !isKnownActor(next, unitId) || !isLiveActor(next, unitId)) return next
  return addTrack(next, event, intent, {
    unitId,
    duration,
    intensity: intent === 'stun' || intent === 'formation_change' ? 'medium' : 'small',
    role: intent,
  })
}

function addRevive(
  state: PresentationTimelineState,
  event: CombatEvent,
): PresentationTimelineState {
  let next = unitRequiredDiagnostic(state, event, event.unit_id, 'unit')
  if (!event.unit_id || !isKnownActor(next, event.unit_id)) return next

  const reviveTrack = addTrack(next, event, 'revive', {
    unitId: event.unit_id,
    duration: 0.32,
    intensity: 'large',
    role: 'revive',
  })
  const { [event.unit_id]: _wasDead, ...remainingDeadActors } = reviveTrack.deadActors
  return { ...reviveTrack, deadActors: remainingDeadActors }
}

export function reducePresentationTimeline(
  state: PresentationTimelineState,
  event: CombatEvent,
): PresentationTimelineState {
  let next = registerActorsFromInit(state, event)

  switch (event.type) {
    case 'animation_start': {
      next = liveActorDiagnostic(next, event, event.attacker_id, 'attacker')
      next = liveActorDiagnostic(next, event, event.target_id, 'target')
      if (!event.attacker_id || !event.target_id || !isKnownActor(next, event.attacker_id) || !isKnownActor(next, event.target_id) || !isLiveActor(next, event.attacker_id) || !isLiveActor(next, event.target_id)) return next
      const withContractDiagnostics = animationContractDiagnostic(next, event)
      if (withContractDiagnostics !== next) return withContractDiagnostics

      return addTrack(next, event, isRangedCombatAnimation(event) ? 'ranged_projectile' : 'melee_lunge', {
        unitId: event.attacker_id,
        targetId: event.target_id,
        duration: event.duration ?? DEFAULT_LUNGE_DURATION_SECONDS,
        intensity: event.bonus_attack ? 'large' : 'medium',
        role: 'attack',
      })
    }

    case 'attack':
    case 'unit_attack':
    case 'damage': {
      next = liveActorDiagnostic(next, event, event.target_id, 'target')
      const targetId = event.target_id
      if (!targetId) return next
      const dodged = event.type === 'unit_attack' && event.dodged === true
      const shieldHit = !dodged && Number(event.shield_absorbed || 0) > 0
      return addTargetImpact(next, event, targetId, dodged ? 'dodge' : shieldHit ? 'shield_hit' : 'target_recoil', dodged ? 'dodge' : shieldHit ? 'shield' : 'impact', event.attacker_id || event.source_id)
    }

    case 'damage_dodged': {
      next = liveActorDiagnostic(next, event, event.target_id, 'target')
      const targetId = event.target_id
      if (!targetId) return next
      return addTargetImpact(next, event, targetId, 'dodge', 'dodge', event.attacker_id || event.source_id)
    }

    case 'attack_missed':
    case 'miss': {
      next = liveActorDiagnostic(next, event, event.target_id, 'target')
      if (!event.target_id) return next
      return addTargetImpact(next, event, event.target_id, 'dodge', 'miss', event.attacker_id || event.source_id)
    }

    case 'multi_hit': {
      const targetIds = Array.isArray(event.target_ids)
        ? event.target_ids.filter((targetId): targetId is string => typeof targetId === 'string' && targetId.trim() !== '')
        : []
      if (targetIds.length === 0) {
        return addDiagnostic(next, event, {
          code: 'missing_target',
          message: `Presentation event ${event.type} seq=${event.seq ?? 'n/a'} event_id=${event.event_id ?? 'n/a'} is missing its target id list.`,
        })
      }
      return targetIds.reduce((current, targetId, targetIndex) => (
        addTargetImpact(current, event, targetId, event.shield_absorbed ? 'shield_hit' : 'multi_hit', `multi-hit:${targetIndex}:${targetId}`, event.attacker_id || event.source_id)
      ), next)
    }

    case 'unit_died': {
      next = unitRequiredDiagnostic(next, event, event.unit_id, 'unit')
      if (!event.unit_id || !isKnownActor(next, event.unit_id)) return next
      if (!isLiveActor(next, event.unit_id)) {
        return addDiagnostic(next, event, {
          code: 'dead_actor',
          unitId: event.unit_id,
          message: `Presentation event ${event.type} seq=${event.seq ?? 'n/a'} event_id=${event.event_id ?? 'n/a'} repeats death for already dead actor ${event.unit_id}.`,
        })
      }
      const deathTrack = addTrack(next, event, 'death', {
        unitId: event.unit_id,
        duration: 0.28,
        intensity: 'large',
        role: 'death',
      })
      return { ...deathTrack, deadActors: { ...deathTrack.deadActors, [event.unit_id]: true } }
    }

    case 'unit_revived':
    case 'revive': {
      return addRevive(next, event)
    }

    case 'shield_broken': {
      next = liveActorDiagnostic(next, event, event.unit_id || event.target_id, 'unit')
      const unitId = event.unit_id || event.target_id
      if (!unitId || !isKnownActor(next, unitId) || !isLiveActor(next, unitId)) return next
      return addTrack(next, event, 'shield_break', {
        unitId,
        targetId: event.target_id || unitId,
        duration: 0.2,
        intensity: 'medium',
        role: 'shield-break',
      })
    }

    case 'shield_applied':
      return addUnitStatus(next, event, 'shield')
    case 'effect_applied':
      return addUnitStatus(next, event, hasItemContext(event) ? 'item' : 'effect')
    case 'stat_buff':
      return addUnitStatus(next, event, hasItemContext(event) ? 'item' : 'buff')
    case 'passive_triggered':
      return addUnitStatus(next, event, hasItemContext(event) ? 'item' : 'passive')
    case 'unit_stunned':
      return addUnitStatus(next, event, 'stun', 0.26)
    case 'unit_heal':
    case 'heal':
      if (event.cause === 'set2_revive') return addRevive(next, event)
      return addUnitStatus(next, event, 'heal')
    case 'hp_regen':
    case 'regen_gain':
      return addUnitStatus(next, event, 'heal')
    case 'damage_over_time_applied':
    case 'damage_over_time_expired':
      return addUnitStatus(next, event, 'damage_over_time')
    case 'damage_over_time_tick': {
      next = liveActorDiagnostic(next, event, event.unit_id, 'target')
      if (!event.unit_id || !isKnownActor(next, event.unit_id) || !isLiveActor(next, event.unit_id)) return next
      return addTargetImpact(next, event, event.unit_id, Number(event.shield_absorbed || 0) > 0 ? 'shield_hit' : 'target_recoil', 'dot-tick', event.source_id || event.caster_id)
    }
    case 'effect_expired':
      return addUnitStatus(next, event, hasItemContext(event) ? 'item' : 'effect')
    case 'formation_changed': {
      next = liveActorDiagnostic(next, event, event.unit_id, 'unit')
      if (!event.unit_id || !isKnownActor(next, event.unit_id) || !isLiveActor(next, event.unit_id)) return next
      return addTrack(next, event, 'formation_change', {
        unitId: event.unit_id,
        duration: 0.28,
        intensity: 'medium',
        role: 'formation-change',
      })
    }

    default:
      if (getPresentationCoverage(event.type) === 'unknown') {
        return addDiagnostic(next, event, {
          code: 'unknown_presentation_event',
          message: `No presentation mapping is registered for event ${event.type} seq=${event.seq ?? 'n/a'} event_id=${event.event_id ?? 'n/a'}.`,
        })
      }
      return next
  }
}

export function buildPresentationTimeline(events: CombatEvent[], index: number): PresentationTimelineState {
  let state = createPresentationTimeline()
  const end = Math.min(index, events.length - 1)
  for (let eventIndex = 0; eventIndex <= end; eventIndex += 1) {
    state = reducePresentationTimeline(state, events[eventIndex])
  }
  return state
}

export function getActivePresentationTracks(
  state: PresentationTimelineState,
  currentTime: number,
): PresentationTrack[] {
  return Object.values(state.tracks)
    .filter((track) => currentTime >= track.startedAt && currentTime <= track.startedAt + track.duration)
    .sort((left, right) => (
      PRESENTATION_INTENSITY_RANK[right.intensity] - PRESENTATION_INTENSITY_RANK[left.intensity]
      || compareStableIds(left.id, right.id)
    ))
}
