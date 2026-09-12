import type { CombatEvent } from '../types'

export type PresentationIntent =
  | 'melee_lunge'
  | 'ranged_projectile'
  | 'target_recoil'
  | 'shield_hit'
  | 'dodge'
  | 'death'
  | 'buff'
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
  code: 'missing_actor' | 'missing_target' | 'unknown_presentation_event'
  message: string
  eventType: string
  eventId?: string
  seq?: number
  unitId?: string
}

export interface PresentationTimelineState {
  tracks: Record<string, PresentationTrack>
  diagnostics: PresentationDiagnostic[]
}

export const createPresentationTimeline = (): PresentationTimelineState => ({
  tracks: {},
  diagnostics: [],
})

const DEFAULT_DURATION_SECONDS = 0.18
const DEFAULT_LUNGE_DURATION_SECONDS = 0.2

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
  if (unitId) return state
  const code = role === 'target' ? 'missing_target' : 'missing_actor'
  return addDiagnostic(state, event, {
    code,
    unitId,
    message: `Presentation event ${event.type} seq=${event.seq ?? 'n/a'} is missing its ${role} id.`,
  })
}

function isRangedAnimation(event: CombatEvent): boolean {
  const animationId = (event.animation_id || '').toLowerCase()
  return animationId.includes('ranged') || animationId.includes('projectile')
}

function impactIntensity(event: CombatEvent): PresentationIntensity {
  if (event.bonus_attack) return 'large'
  const damage = Number(event.applied_damage ?? event.damage ?? 0)
  if (Number.isFinite(damage) && damage >= 100) return 'large'
  return 'medium'
}

export function reducePresentationTimeline(
  state: PresentationTimelineState,
  event: CombatEvent,
): PresentationTimelineState {
  let next = state

  switch (event.type) {
    case 'animation_start': {
      next = unitRequiredDiagnostic(next, event, event.attacker_id, 'attacker')
      next = unitRequiredDiagnostic(next, event, event.target_id, 'target')
      if (!event.attacker_id || !event.target_id) return next

      return addTrack(next, event, isRangedAnimation(event) ? 'ranged_projectile' : 'melee_lunge', {
        unitId: event.attacker_id,
        targetId: event.target_id,
        duration: event.duration ?? DEFAULT_LUNGE_DURATION_SECONDS,
        intensity: event.bonus_attack ? 'large' : 'medium',
        role: 'attack',
      })
    }

    case 'unit_attack':
    case 'damage': {
      next = unitRequiredDiagnostic(next, event, event.target_id || event.unit_id, 'target')
      const targetId = event.target_id || event.unit_id
      if (!targetId) return next
      const dodged = event.type === 'unit_attack' && event.dodged === true
      const shieldHit = !dodged && Number(event.shield_absorbed || 0) > 0
      return addTrack(next, event, dodged ? 'dodge' : shieldHit ? 'shield_hit' : 'target_recoil', {
        targetId,
        duration: 0.16,
        intensity: impactIntensity(event),
        role: dodged ? 'dodge' : shieldHit ? 'shield' : 'impact',
      })
    }

    case 'damage_dodged': {
      next = unitRequiredDiagnostic(next, event, event.target_id || event.unit_id, 'target')
      const targetId = event.target_id || event.unit_id
      if (!targetId) return next
      return addTrack(next, event, 'dodge', {
        targetId,
        duration: 0.16,
        intensity: 'medium',
        role: 'dodge',
      })
    }

    case 'unit_died': {
      next = unitRequiredDiagnostic(next, event, event.unit_id, 'unit')
      if (!event.unit_id) return next
      return addTrack(next, event, 'death', {
        unitId: event.unit_id,
        duration: 0.28,
        intensity: 'large',
        role: 'death',
      })
    }

    case 'unit_revived':
    case 'revive': {
      next = unitRequiredDiagnostic(next, event, event.unit_id, 'unit')
      if (!event.unit_id) return next
      return addTrack(next, event, 'revive', {
        unitId: event.unit_id,
        duration: 0.32,
        intensity: 'large',
        role: 'revive',
      })
    }

    case 'shield_applied':
    case 'effect_applied':
    case 'stat_buff':
    case 'passive_triggered':
    case 'unit_heal':
    case 'heal':
    case 'hp_regen':
    case 'regen_gain': {
      next = unitRequiredDiagnostic(next, event, event.unit_id || event.caster_id, 'unit')
      const unitId = event.unit_id || event.caster_id
      if (!unitId) return next
      return addTrack(next, event, 'buff', {
        unitId,
        duration: 0.22,
        intensity: 'small',
        role: 'buff',
      })
    }

    default:
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
    .sort((left, right) => right.intensity.localeCompare(left.intensity) || left.id.localeCompare(right.id))
}
