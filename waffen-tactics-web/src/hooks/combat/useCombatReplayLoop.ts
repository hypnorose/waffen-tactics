import { Dispatch, MutableRefObject, SetStateAction, useCallback, useEffect, useRef } from 'react'
import { getReplaySchedule } from './replayController'
import { processReplayEvent } from './replayEventProcessor'
import type { CombatEvent, CombatState, DesyncEntry } from './types'

interface UseCombatReplayLoopOptions {
  bufferedEvents: CombatEvent[]
  isBufferedComplete: boolean
  combatError: unknown
  replayEnabled: boolean
  replayPaused: boolean
  combatSpeed: number
  playhead: number
  combatStateRef: MutableRefObject<CombatState>
  recentEventsRef: MutableRefObject<CombatEvent[]>
  lastAppliedPlayheadRef: MutableRefObject<number>
  recordPresentationEvent: (event: CombatEvent) => void
  resetPresentation: () => void
  onDesync: (entry: DesyncEntry) => void
  setCombatState: Dispatch<SetStateAction<CombatState>>
  setStoredGoldBreakdown: Dispatch<SetStateAction<{
    base: number
    interest: number
    milestone: number
    win_bonus: number
    total: number
    item_parts: string[]
  } | null>>
  setPlayhead: Dispatch<SetStateAction<number>>
  setAllEventsReplayed: Dispatch<SetStateAction<boolean>>
  setReplayPaused: Dispatch<SetStateAction<boolean>>
  setReplaySeekError: Dispatch<SetStateAction<string | null>>
}

/**
 * Owns autoplay and transport lifecycle for a canonical combat replay.
 * State mutation remains delegated to the shared replay event processor; the
 * overlay only composes the returned domain state with presentation hooks.
 */
export function useCombatReplayLoop({
  bufferedEvents,
  isBufferedComplete,
  combatError,
  replayEnabled,
  replayPaused,
  combatSpeed,
  playhead,
  combatStateRef,
  recentEventsRef,
  lastAppliedPlayheadRef,
  recordPresentationEvent,
  resetPresentation,
  onDesync,
  setCombatState,
  setStoredGoldBreakdown,
  setPlayhead,
  setAllEventsReplayed,
  setReplayPaused,
  setReplaySeekError,
}: UseCombatReplayLoopOptions) {
  const replayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const replayInitializedRef = useRef(false)
  const prevReplayEnabledRef = useRef(replayEnabled)

  const clearReplayTimer = useCallback(() => {
    if (replayTimerRef.current) {
      clearTimeout(replayTimerRef.current)
      replayTimerRef.current = null
    }
  }, [])

  const scheduleNextEvent = useCallback((currentPlayhead: number) => {
    const schedule = getReplaySchedule(bufferedEvents, currentPlayhead, isBufferedComplete, combatSpeed)
    if (schedule.kind === 'complete') {
      setAllEventsReplayed(true)
      return
    }
    if (schedule.kind === 'wait') return

    clearReplayTimer()
    replayTimerRef.current = setTimeout(() => {
      // Guard against stale timers if playhead changed elsewhere.
      setPlayhead(previous => (previous === currentPlayhead ? schedule.nextIndex : previous))
    }, schedule.delayMs)
  }, [bufferedEvents, isBufferedComplete, combatSpeed, setAllEventsReplayed, clearReplayTimer, setPlayhead])

  // A typed transport error terminates the committed batch. Keep any already
  // received canonical events available for inspection, but never continue
  // applying them or present the replay as playable after the stream stops.
  useEffect(() => {
    if (!combatError) return
    clearReplayTimer()
    setReplayPaused(true)
    setAllEventsReplayed(false)
    setReplaySeekError(null)
  }, [combatError, clearReplayTimer, setReplayPaused, setAllEventsReplayed, setReplaySeekError])

  // Replay loop
  useEffect(() => {
    console.log('[REPLAY LOOP] Running. replayEnabled:', replayEnabled, 'bufferedEvents.length:', bufferedEvents.length)

    if (!replayEnabled) {
      console.log('[REPLAY LOOP] Gate closed, clearing timer')
      clearReplayTimer()
      return
    }

    if (combatError) {
      clearReplayTimer()
      return
    }

    if (replayPaused) {
      clearReplayTimer()
      return
    }

    if (playhead >= bufferedEvents.length) {
      console.log('[REPLAY LOOP] Playhead reached end')
      clearReplayTimer()
      return
    }

    // If the effect reruns for the same event (e.g. speed changes), do not
    // reapply state mutation — only reschedule the next step timing.
    if (playhead <= lastAppliedPlayheadRef.current) {
      scheduleNextEvent(playhead)
      return
    }

    const event = bufferedEvents[playhead]
    console.log('Applying event:', event.type, 'seq:', event.seq, 'playhead:', playhead)

    recentEventsRef.current = [...recentEventsRef.current, event].slice(-50)

    const result = processReplayEvent({
      currentState: combatStateRef.current,
      event,
      pendingEvents: bufferedEvents.slice(playhead + 1, playhead + 26),
    })

    if (result.goldBreakdown) setStoredGoldBreakdown(result.goldBreakdown)
    result.desyncs.forEach(onDesync)

    if (!result.state) {
      clearReplayTimer()
      setReplayPaused(true)
      setReplaySeekError(`Replay zatrzymany na seq=${event.seq ?? 'unknown'}. Otwórz Desync log.`)
      if (result.validationError) {
        console.error(`🛑 Combat replay stopped at seq=${event.seq} due to validation failure`, result.validationError)
      }
      return
    }

    lastAppliedPlayheadRef.current = playhead
    const newState = result.state
    setCombatState(newState)
    combatStateRef.current = newState

    // Presentation is a separate, visual-only projection of the same event.
    recordPresentationEvent(event)

    if (result.shouldStop) {
      console.error(`🛑 Combat stopped at seq=${event.seq} due to replay validation/desync diagnostics`)
      clearReplayTimer()
      setReplayPaused(true)
      setReplaySeekError(`Replay zatrzymany na seq=${event.seq ?? 'unknown'} z powodu desyncu. Otwórz Desync log.`)
      return
    }

    scheduleNextEvent(playhead)
  }, [replayEnabled, replayPaused, combatError, bufferedEvents, playhead, clearReplayTimer, lastAppliedPlayheadRef, scheduleNextEvent, combatStateRef, recentEventsRef, setStoredGoldBreakdown, onDesync, setCombatState, recordPresentationEvent, setPlayhead])

  // Start replay when buffered
  useEffect(() => {
    const justEnabled = replayEnabled && !prevReplayEnabledRef.current
    console.log('[REPLAY INIT] Running. replayEnabled:', replayEnabled, 'justEnabled:', justEnabled, 'bufferedEvents.length:', bufferedEvents.length, 'replayInitialized:', replayInitializedRef.current, 'lastAppliedPlayhead:', lastAppliedPlayheadRef.current)
    prevReplayEnabledRef.current = replayEnabled

    if (!replayEnabled) {
      console.log('[REPLAY INIT] Gate not enabled, skipping')
      return
    }
    if (combatError) {
      console.log('[REPLAY INIT] Combat transport error, replay remains stopped')
      return
    }
    if (bufferedEvents.length === 0) {
      console.log('[REPLAY INIT] No events yet, skipping')
      return
    }

    // Progressive buffering updates bufferedEvents many times during one
    // fight. Initialize autoplay once per stream; do not reset on append.
    if (replayInitializedRef.current && !justEnabled) {
      console.log('[REPLAY INIT] Already initialized and not justEnabled, skipping')
      return
    }

    if (justEnabled && lastAppliedPlayheadRef.current >= 0) {
      console.log('[REPLAY INIT] justEnabled but replay already in progress (lastApplied:', lastAppliedPlayheadRef.current, '), skipping reset')
      replayInitializedRef.current = true
      return
    }

    console.log('[REPLAY INIT] ✅ Initializing replay!')
    replayInitializedRef.current = true
    clearReplayTimer()
    lastAppliedPlayheadRef.current = -1
    recentEventsRef.current = []
    setAllEventsReplayed(false)
    setReplayPaused(false)
    setReplaySeekError(null)
    resetPresentation()
    setPlayhead(0)
  }, [replayEnabled, bufferedEvents, combatError, clearReplayTimer, lastAppliedPlayheadRef, recentEventsRef, setAllEventsReplayed, setReplayPaused, setReplaySeekError, resetPresentation, setPlayhead])

  useEffect(() => {
    return () => {
      clearReplayTimer()
      replayInitializedRef.current = false
    }
  }, [clearReplayTimer])

  return { clearReplayTimer }
}
