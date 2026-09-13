import { Dispatch, MutableRefObject, SetStateAction, useCallback } from 'react'
import { createEmptyCombatState, reconstructCombatState } from './replayController'
import type { CombatEvent, CombatState } from './types'

interface UseCombatReplayControlsOptions {
  bufferedEvents: CombatEvent[]
  isBufferedComplete: boolean
  replayPaused: boolean
  clearReplayTimerAndPause: () => void
  rebuildPresentation: (events: CombatEvent[], index: number) => void
  combatStateRef: MutableRefObject<CombatState>
  recentEventsRef: MutableRefObject<CombatEvent[]>
  lastAppliedPlayheadRef: MutableRefObject<number>
  setCombatState: Dispatch<SetStateAction<CombatState>>
  setPlayhead: Dispatch<SetStateAction<number>>
  setAllEventsReplayed: Dispatch<SetStateAction<boolean>>
  setReplaySeekError: Dispatch<SetStateAction<string | null>>
  setReplayPaused: Dispatch<SetStateAction<boolean>>
}

/**
 * Owns user-driven replay navigation while the overlay remains responsible
 * only for composing the resulting combat state and presentation layers.
 */
export function useCombatReplayControls({
  bufferedEvents,
  isBufferedComplete,
  replayPaused,
  clearReplayTimerAndPause,
  rebuildPresentation,
  combatStateRef,
  recentEventsRef,
  lastAppliedPlayheadRef,
  setCombatState,
  setPlayhead,
  setAllEventsReplayed,
  setReplaySeekError,
  setReplayPaused,
}: UseCombatReplayControlsOptions) {
  const seekReplay = useCallback((targetIndex: number) => {
    clearReplayTimerAndPause()

    try {
      const reconstructed = reconstructCombatState(bufferedEvents, targetIndex, createEmptyCombatState())
      setReplaySeekError(null)
      setCombatState(reconstructed)
      combatStateRef.current = reconstructed
      rebuildPresentation(bufferedEvents, targetIndex)
      recentEventsRef.current = bufferedEvents.slice(0, targetIndex + 1).slice(-50)
      lastAppliedPlayheadRef.current = targetIndex
      setPlayhead(Math.max(0, targetIndex))
      setAllEventsReplayed(isBufferedComplete && targetIndex === bufferedEvents.length - 1)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Nie udało się odtworzyć wybranego stanu replayu.'
      setReplaySeekError(message)
    }
  }, [bufferedEvents, isBufferedComplete, clearReplayTimerAndPause, rebuildPresentation, combatStateRef, recentEventsRef, lastAppliedPlayheadRef, setCombatState, setPlayhead, setAllEventsReplayed, setReplaySeekError])

  const restartReplay = useCallback(() => {
    if (bufferedEvents.length === 0) {
      setReplaySeekError('Replay nie ma jeszcze żadnych zdarzeń do odtworzenia.')
      return
    }
    seekReplay(0)
  }, [bufferedEvents.length, seekReplay, setReplaySeekError])

  const toggleReplay = useCallback(() => {
    if (replayPaused) {
      setReplaySeekError(null)
      setReplayPaused(false)
      return
    }
    clearReplayTimerAndPause()
  }, [replayPaused, setReplaySeekError, setReplayPaused, clearReplayTimerAndPause])

  return { restartReplay, toggleReplay, seekReplay }
}
