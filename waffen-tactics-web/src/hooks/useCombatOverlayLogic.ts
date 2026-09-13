import { useState, useEffect, useRef, useCallback, MutableRefObject } from 'react'
import { PlayerState } from '../store/gameStore'
import { useAuthStore } from '../store/authStore'
import { useCombatSSEBuffer } from './combat/useCombatSSEBuffer'
import { normalizeCombatSpeed } from './combat/replayTiming'
import { createEmptyCombatState } from './combat/replayController'
import { useCombatPresentation } from './combat/useCombatPresentation'
import { useCombatReplayCompletion } from './combat/useCombatReplayCompletion'
import { useCombatReplayControls } from './combat/useCombatReplayControls'
import { useCombatReplayLoop } from './combat/useCombatReplayLoop'
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

  const pushDesync = useCallback((entry: DesyncEntry) => {
    const recent_events = recentEventsRef.current.slice(-25)
    setDesyncLogs(prev => {
      return [{ ...entry, recent_events }, ...prev].slice(0, 200)
    })
  }, [])

  const clearDesyncLogs = () => setDesyncLogs([])

  const { clearReplayTimer } = useCombatReplayLoop({
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
    onDesync: pushDesync,
    setCombatState,
    setStoredGoldBreakdown,
    setPlayhead,
    setAllEventsReplayed,
    setReplayPaused,
    setReplaySeekError,
  })

  const clearReplayTimerAndPause = () => {
    clearReplayTimer()
    cancelReplayCompletionCleanup()
    clearPresentationTracks()
    setReplayPaused(true)
  }

  const { restartReplay, toggleReplay, seekReplay } = useCombatReplayControls({
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
  })

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
