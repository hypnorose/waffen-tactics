import { useState, useEffect, useRef, MutableRefObject } from 'react'
import { PlayerState } from '../store/gameStore'
import { useAuthStore } from '../store/authStore'
import { useCombatSSEBuffer } from './combat/useCombatSSEBuffer'
import { normalizeCombatSpeed } from './combat/replayTiming'
import { createEmptyCombatState, getReplaySchedule, reconstructCombatState } from './combat/replayController'
import { processReplayEvent } from './combat/replayEventProcessor'
import { useCombatPresentation } from './combat/useCombatPresentation'
import { useCombatReplayCompletion } from './combat/useCombatReplayCompletion'
import { CombatState, CombatEvent, CombatUnitRoundStats, DesyncEntry } from './combat/types'

interface UseCombatOverlayLogicProps {
  onClose: (newState?: PlayerState, roundStatsByUnit?: Record<string, CombatUnitRoundStats>) => void
  logEndRef: MutableRefObject<HTMLDivElement | null>
  replayEnabled?: boolean
}

export function useCombatOverlayLogic({ onClose, logEndRef, replayEnabled = true }: UseCombatOverlayLogicProps) {
  const { token } = useAuthStore()
  const { bufferedEvents, isBufferedComplete, combatError } = useCombatSSEBuffer(token || '')
  const [playhead, setPlayhead] = useState(0)
  const [combatState, setCombatState] = useState<CombatState>(createEmptyCombatState)
  const combatStateRef = useRef(combatState)

  useEffect(() => {
    combatStateRef.current = combatState
  }, [combatState])
  const [showLog, setShowLog] = useState(false)
  const [combatSpeed, setCombatSpeed] = useState(() => {
    const saved = localStorage.getItem('combatSpeed')
    return normalizeCombatSpeed(saved)
  })
  const [desyncLogs, setDesyncLogs] = useState<DesyncEntry[]>([])
  const [storedGoldBreakdown, setStoredGoldBreakdown] = useState<{ base: number, interest: number, milestone: number, win_bonus: number, total: number, item_parts: string[] } | null>(null)
  const [displayedGoldBreakdown, setDisplayedGoldBreakdown] = useState<{ base: number, interest: number, milestone: number, win_bonus: number, total: number, item_parts: string[] } | null>(null)

  const [allEventsReplayed, setAllEventsReplayed] = useState(false)
  const [replayPaused, setReplayPaused] = useState(false)
  const [replaySeekError, setReplaySeekError] = useState<string | null>(null)
  const recentEventsRef = useRef<CombatEvent[]>([])
  const lastAppliedPlayheadRef = useRef<number>(-1)
  const replayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const replayInitializedRef = useRef<boolean>(false)
  const prevReplayEnabledRef = useRef<boolean>(replayEnabled)

  const clearReplayTimer = () => {
    if (replayTimerRef.current) {
      clearTimeout(replayTimerRef.current)
      replayTimerRef.current = null
    }
  }

  const {
    activeTracks: presentationTracks,
    diagnostics: presentationDiagnostics,
    reducedMotion,
    pendingVisuals,
    recordEvent: recordPresentationEvent,
    reportDiagnostic: reportPresentationDiagnostic,
    rebuild: rebuildPresentation,
    clearTracks: clearPresentationTracks,
    reset: resetPresentation,
  } = useCombatPresentation({ currentTime: combatState.simTime, replayPaused })

  const { cancelCleanup: cancelReplayCompletionCleanup } = useCombatReplayCompletion({
    allEventsReplayed,
    pendingVisuals,
    clearPresentationTracks,
    setCombatState,
    combatStateRef,
  })

  const scheduleNextEvent = (currentPlayhead: number) => {
    const schedule = getReplaySchedule(bufferedEvents, currentPlayhead, isBufferedComplete, combatSpeed)
    if (schedule.kind === 'complete') {
      setAllEventsReplayed(true)
      return
    }
    if (schedule.kind === 'wait') return

    clearReplayTimer()
    replayTimerRef.current = setTimeout(() => {
      // Guard against stale timers if playhead changed elsewhere.
      setPlayhead(prev => (prev === currentPlayhead ? schedule.nextIndex : prev))
    }, schedule.delayMs)
  }

  const pushDesync = (entry: DesyncEntry) => {
    const recent_events = recentEventsRef.current.slice(-25)
    setDesyncLogs(prev => {
      return [{ ...entry, recent_events }, ...prev].slice(0, 200)
    })
  }

  const clearDesyncLogs = () => setDesyncLogs([])

  const clearReplayTimerAndPause = () => {
    clearReplayTimer()
    cancelReplayCompletionCleanup()
    clearPresentationTracks()
    setReplayPaused(true)
  }

  // A typed transport error terminates the committed batch. Keep any already
  // received canonical events available for inspection, but never continue
  // applying them or present the replay as playable after the stream stops.
  useEffect(() => {
    if (!combatError) return
    clearReplayTimer()
    setReplayPaused(true)
    setAllEventsReplayed(false)
    setReplaySeekError(null)
  }, [combatError])

  const seekReplay = (targetIndex: number) => {
    clearReplayTimerAndPause()

    try {
      const reconstructed = reconstructCombatState(bufferedEvents, targetIndex)
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
  }

  const restartReplay = () => {
    if (bufferedEvents.length === 0) {
      setReplaySeekError('Replay nie ma jeszcze żadnych zdarzeń do odtworzenia.')
      return
    }
    seekReplay(0)
  }

  const toggleReplay = () => {
    if (replayPaused) {
      setReplaySeekError(null)
      setReplayPaused(false)
      return
    }
    clearReplayTimerAndPause()
  }

  const exportDesyncJSON = () => {
    try {
      return JSON.stringify(desyncLogs, null, 2)
    } catch (err) {
      console.error('Failed to stringify desyncLogs', err)
      return '[]'
    }
  }

  // Persist settings
  useEffect(() => {
    try {
      localStorage.setItem('combatSpeed', combatSpeed.toString())
    } catch (err) {}
  }, [combatSpeed])

  // Replay loop
  useEffect(() => {
    console.log('[REPLAY LOOP] Running. replayEnabled:', replayEnabled, 'playhead:', playhead, 'bufferedEvents.length:', bufferedEvents.length)
    
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

    const event = bufferedEvents[playhead]

    // If the effect reruns for the same event (e.g. speed slider changes),
    // do NOT reapply state mutation — only reschedule next step timing.
    if (playhead <= lastAppliedPlayheadRef.current) {
      scheduleNextEvent(playhead)
      return
    }

    console.log('Applying event:', event.type, 'seq:', event.seq, 'playhead:', playhead)

    // Keep a rolling buffer of recent events for desync diagnostics
    recentEventsRef.current = [...recentEventsRef.current, event].slice(-50)

    const currentState = combatStateRef.current
    const result = processReplayEvent({
      currentState,
      event,
      pendingEvents: bufferedEvents.slice(playhead + 1, playhead + 26),
    })

    if (result.goldBreakdown) setStoredGoldBreakdown(result.goldBreakdown)
    result.desyncs.forEach(pushDesync)

    if (!result.state) {
      clearReplayTimer()
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
    // It never writes to the authoritative combat state or derives damage.
    recordPresentationEvent(event)

    if (result.shouldStop) {
      console.error(`🛑 Combat stopped at seq=${event.seq} due to replay validation/desync diagnostics`)
      clearReplayTimer()
      return
    }

    // Schedule next
    scheduleNextEvent(playhead)
  }, [replayEnabled, replayPaused, combatError, isBufferedComplete, bufferedEvents, playhead, combatSpeed, recordPresentationEvent])

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

    // Progressive buffering updates `bufferedEvents` many times during one fight.
    // Initialize autoplay once per stream; do not reset playhead on each append.
    // But when replay gate is opened (after matchmaking screen), always bootstrap.
    // CRITICAL: Don't reset playhead if replay already started (would cancel scheduled timers!)
    if (replayInitializedRef.current && !justEnabled) {
      console.log('[REPLAY INIT] Already initialized and not justEnabled, skipping')
      return
    }
    
    // If justEnabled but we already applied events, don't reset - replay is in progress!
    if (justEnabled && lastAppliedPlayheadRef.current >= 0) {
      console.log('[REPLAY INIT] justEnabled but replay already in progress (lastApplied:', lastAppliedPlayheadRef.current, '), skipping reset')
      replayInitializedRef.current = true  // Mark as initialized so we don't re-run
      return
    }
    
    console.log('[REPLAY INIT] ✅ Initializing replay! Setting playhead to 0')
    replayInitializedRef.current = true

    // New fight loaded -> always autostart replay from beginning.
    clearReplayTimer()
    lastAppliedPlayheadRef.current = -1
    recentEventsRef.current = []
    setAllEventsReplayed(false)
    setReplayPaused(false)
    setReplaySeekError(null)
    resetPresentation()
    setPlayhead(0)
  }, [replayEnabled, bufferedEvents, combatError, resetPresentation])

  useEffect(() => {
    return () => {
      clearReplayTimer()
      replayInitializedRef.current = false
    }
  }, [])

  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [combatState.combatLog])

  const handleClose = () => onClose(combatState.finalState || undefined, combatState.combatSummary?.unitStatsByUnit)
  const handleGoldDismiss = () => { setDisplayedGoldBreakdown(null); setStoredGoldBreakdown(null); handleClose() }

  const hasCombatInitData =
    combatState.playerUnits.length > 0 ||
    combatState.opponentUnits.length > 0 ||
    !!combatState.opponentInfo

  const isSearchingOpponent = !combatError && !hasCombatInitData && bufferedEvents.length === 0 && !isBufferedComplete

  return {
    playerUnits: combatState.playerUnits,
    opponentUnits: combatState.opponentUnits,
    combatLog: combatState.combatLog,
    isFinished: combatState.isFinished,
    victory: combatState.victory,
    finalState: combatState.finalState,
    synergies: combatState.synergies,
    traits: combatState.traits,
    opponentInfo: combatState.opponentInfo,
    showLog,
    setShowLog,
    // attack animation state removed; projectiles are used instead
    combatSpeed,
    setCombatSpeed,
    regenMap: combatState.regenMap,
    storedGoldBreakdown,
    displayedGoldBreakdown,
    setDisplayedGoldBreakdown,
    setStoredGoldBreakdown,
    handleClose,
    handleGoldDismiss,
    defeatMessage: combatState.defeatMessage,
    combatSummary: combatState.combatSummary,
    simTime: combatState.simTime,
    presentationTracks,
    presentationDiagnostics,
    reducedMotion,
    replayPaused,
    reportPresentationDiagnostic,
    replayEvents: bufferedEvents,
    replayEventIndex: bufferedEvents.length > 0 ? Math.min(playhead, bufferedEvents.length - 1) : 0,
    replayPlaying: replayEnabled && !combatError && !replayPaused && bufferedEvents.length > 0,
    replaySeekError,
    combatError,
    restartReplay,
    toggleReplay,
    seekReplay,
    activeAttackerId: combatState.combatSummary?.focus?.attacker_id ?? null,
    activeTargetId: combatState.combatSummary?.focus?.target_id ?? null,
    desyncLogs,
    clearDesyncLogs,
    exportDesyncJSON,
    isSearchingOpponent
  }
}
