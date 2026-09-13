import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useProjectileSystem } from '../useProjectileSystem'
import {
  getCombatAttackProjectileEmoji,
  hasCanonicalAnimationIdentity,
  isRangedCombatAnimation,
} from './combatPresentation'
import type { CombatEvent } from './types'
import {
  buildPresentationTimeline,
  clearPresentationTracks,
  createPresentationTimeline,
  getActivePresentationTracks,
  pruneExpiredPresentationTracks,
  reducePresentationTimeline,
  type PresentationTimelineState,
  type PresentationDiagnostic,
  type PresentationTrack,
} from './animation/presentationTimeline'

interface UseCombatPresentationOptions {
  currentTime: number
  replayPaused: boolean
}

function usePrefersReducedMotion(): boolean {
  const [reducedMotion, setReducedMotion] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReducedMotion(mediaQuery.matches)
    update()
    mediaQuery.addEventListener?.('change', update)
    return () => mediaQuery.removeEventListener?.('change', update)
  }, [])

  return reducedMotion
}

export function useCombatPresentation({ currentTime, replayPaused }: UseCombatPresentationOptions) {
  const { spawnProjectile, clearProjectiles } = useProjectileSystem()
  const [timeline, setTimeline] = useState(createPresentationTimeline)
  const timelineRef = useRef<PresentationTimelineState>(createPresentationTimeline())
  const [pendingVisuals, setPendingVisuals] = useState(0)
  const reducedMotion = usePrefersReducedMotion()

  const recordEvent = useCallback((event: CombatEvent) => {
    const eventTime = typeof event.timestamp === 'number' && Number.isFinite(event.timestamp)
      ? event.timestamp
      : 0
    const previousTimeline = pruneExpiredPresentationTracks(timelineRef.current, eventTime)
    const nextTimeline = reducePresentationTimeline(
      previousTimeline,
      event,
    )
    timelineRef.current = nextTimeline
    setTimeline(nextTimeline)

    // Keep the existing projectile feedback behind the presentation boundary.
    // It is visual-only and completes independently of the authoritative reducer.
    // Only spawn when this exact event produced a new ranged track. This keeps
    // the imperative projectile layer aligned with timeline dedupe and also
    // prevents VFX for invalid/dead-target animation_start diagnostics.
    const createdRangedTrack = event.type === 'animation_start' &&
      typeof event.event_id === 'string' &&
      Object.values(nextTimeline.tracks).some((track) => (
        !previousTimeline.tracks[track.id] &&
        track.intent === 'ranged_projectile' && track.sourceEventId === event.event_id
      ))
    if (!reducedMotion && hasCanonicalAnimationIdentity(event) && createdRangedTrack && isRangedCombatAnimation(event) && event.attacker_id && event.target_id) {
      setPendingVisuals((count) => count + 1)
      spawnProjectile({
        id: `projectile:${event.event_id}`,
        fromId: event.attacker_id,
        toId: event.target_id,
        emoji: getCombatAttackProjectileEmoji(event),
        duration: (event.duration || 0.3) * 1000,
        sourceEventId: event.event_id,
        sourceSeq: event.seq,
        onComplete: () => setPendingVisuals((count) => Math.max(0, count - 1)),
      })
    }

  }, [reducedMotion, spawnProjectile])

  const rebuild = useCallback((events: CombatEvent[], index: number) => {
    clearProjectiles()
    setPendingVisuals(0)
    const nextTimeline = buildPresentationTimeline(events, index)
    timelineRef.current = nextTimeline
    setTimeline(nextTimeline)
  }, [clearProjectiles])

  const clearTracks = useCallback(() => {
    const nextTimeline = clearPresentationTracks(timelineRef.current)
    timelineRef.current = nextTimeline
    setTimeline(nextTimeline)
  }, [])

  const reportDiagnostic = useCallback((diagnostic: PresentationDiagnostic) => {
    const previous = timelineRef.current
    const signature = `${diagnostic.code}:${diagnostic.eventId || diagnostic.eventType}:${diagnostic.seq ?? 'na'}:${diagnostic.unitId || ''}`
    if (previous.diagnostics.some((entry) => `${entry.code}:${entry.eventId || entry.eventType}:${entry.seq ?? 'na'}:${entry.unitId || ''}` === signature)) return
    const nextTimeline = {
      ...previous,
      diagnostics: [...previous.diagnostics, diagnostic].slice(-50),
    }
    timelineRef.current = nextTimeline
    setTimeline(nextTimeline)
  }, [])

  const reset = useCallback(() => {
    clearProjectiles()
    const nextTimeline = createPresentationTimeline()
    timelineRef.current = nextTimeline
    setTimeline(nextTimeline)
    setPendingVisuals(0)
  }, [clearProjectiles])

  useEffect(() => {
    if (!replayPaused) return
    clearProjectiles()
    setPendingVisuals(0)
  }, [clearProjectiles, replayPaused])

  const activeTracks = useMemo<PresentationTrack[]>(
    () => getActivePresentationTracks(timeline, currentTime),
    [currentTime, timeline],
  )

  const diagnostics = timeline.diagnostics

  return {
    activeTracks,
    diagnostics,
    reducedMotion,
    replayPaused,
    pendingVisuals,
    recordEvent,
    reportDiagnostic,
    rebuild,
    clearTracks,
    reset,
  }
}

export type { PresentationDiagnostic, PresentationTrack }
