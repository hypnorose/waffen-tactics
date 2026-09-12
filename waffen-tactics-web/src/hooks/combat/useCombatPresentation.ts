import { useCallback, useEffect, useMemo, useState } from 'react'
import { useProjectileSystem } from '../useProjectileSystem'
import { getCombatAttackProjectileEmoji } from './combatPresentation'
import type { CombatEvent } from './types'
import {
  buildPresentationTimeline,
  createPresentationTimeline,
  getActivePresentationTracks,
  reducePresentationTimeline,
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
  const [pendingVisuals, setPendingVisuals] = useState(0)
  const reducedMotion = usePrefersReducedMotion()

  const recordEvent = useCallback((event: CombatEvent) => {
    setTimeline((previous) => reducePresentationTimeline(previous, event))

    // Keep the existing projectile feedback behind the presentation boundary.
    // It is visual-only and completes independently of the authoritative reducer.
    if (!reducedMotion && event.type === 'animation_start' && event.attacker_id && event.target_id) {
      setPendingVisuals((count) => count + 1)
      spawnProjectile({
        fromId: event.attacker_id,
        toId: event.target_id,
        emoji: getCombatAttackProjectileEmoji(event),
        duration: (event.duration || 0.3) * 1000,
        onComplete: () => setPendingVisuals((count) => Math.max(0, count - 1)),
      })
    }

    // Bonus attacks can have an animation_start predecessor without bonus metadata.
    // Their impact marker therefore starts from the canonical unit_attack event.
    if (!reducedMotion && event.type === 'unit_attack' && event.bonus_attack && event.attacker_id && event.target_id) {
      setPendingVisuals((count) => count + 1)
      spawnProjectile({
        fromId: event.attacker_id,
        toId: event.target_id,
        emoji: getCombatAttackProjectileEmoji(event),
        duration: 220,
        onComplete: () => setPendingVisuals((count) => Math.max(0, count - 1)),
      })
    }
  }, [reducedMotion, spawnProjectile])

  const rebuild = useCallback((events: CombatEvent[], index: number) => {
    clearProjectiles()
    setPendingVisuals(0)
    setTimeline(buildPresentationTimeline(events, index))
  }, [clearProjectiles])

  const reportDiagnostic = useCallback((diagnostic: PresentationDiagnostic) => {
    setTimeline((previous) => {
      const signature = `${diagnostic.code}:${diagnostic.eventId || diagnostic.eventType}:${diagnostic.seq ?? 'na'}:${diagnostic.unitId || ''}`
      if (previous.diagnostics.some((entry) => `${entry.code}:${entry.eventId || entry.eventType}:${entry.seq ?? 'na'}:${entry.unitId || ''}` === signature)) {
        return previous
      }
      return {
        ...previous,
        diagnostics: [...previous.diagnostics, diagnostic].slice(-50),
      }
    })
  }, [])

  const reset = useCallback(() => {
    clearProjectiles()
    setTimeline(createPresentationTimeline())
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
    reset,
  }
}

export type { PresentationDiagnostic, PresentationTrack }
