import { MutableRefObject, Dispatch, SetStateAction, useCallback, useEffect, useRef } from 'react'
import type { CombatState } from './types'

export const TERMINAL_PRESENTATION_CLEANUP_MS = 500

export function shouldFinalizeReplay(allEventsReplayed: boolean, pendingVisuals: number): boolean {
  return allEventsReplayed && pendingVisuals === 0
}

interface UseCombatReplayCompletionOptions {
  allEventsReplayed: boolean
  pendingVisuals: number
  clearPresentationTracks: () => void
  setCombatState: Dispatch<SetStateAction<CombatState>>
  combatStateRef: MutableRefObject<CombatState>
}

/**
 * Owns the terminal replay transition and delayed visual cleanup.
 *
 * The authoritative combat state is finalized as soon as the canonical event
 * stream is complete and no visual projection is pending. Transient tracks
 * remain visible for the final presentation window, then are cleared without
 * changing the replayed state.
 */
export function useCombatReplayCompletion({
  allEventsReplayed,
  pendingVisuals,
  clearPresentationTracks,
  setCombatState,
  combatStateRef,
}: UseCombatReplayCompletionOptions) {
  const cleanupTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const cancelCleanup = useCallback(() => {
    if (cleanupTimerRef.current) {
      clearTimeout(cleanupTimerRef.current)
      cleanupTimerRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!shouldFinalizeReplay(allEventsReplayed, pendingVisuals)) return

    setCombatState(previous => (previous.isFinished ? previous : { ...previous, isFinished: true }))
    combatStateRef.current = { ...combatStateRef.current, isFinished: true }

    cancelCleanup()
    cleanupTimerRef.current = setTimeout(() => {
      clearPresentationTracks()
      cleanupTimerRef.current = null
    }, TERMINAL_PRESENTATION_CLEANUP_MS)

    return cancelCleanup
  }, [allEventsReplayed, pendingVisuals, clearPresentationTracks, setCombatState, combatStateRef, cancelCleanup])

  useEffect(() => cancelCleanup, [cancelCleanup])

  return { cancelCleanup }
}
