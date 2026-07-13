import { useState, useEffect, useRef, MutableRefObject } from 'react'
import { PlayerState } from '../store/gameStore'
import { useAuthStore } from '../store/authStore'
import { useCombatSSEBuffer } from './combat/useCombatSSEBuffer'
import { computeDelayMs } from './combat/replayTiming'
import { applyCombatEvent } from './combat/applyEvent'
import { compareCombatStates } from './combat/desync'
import { useProjectileSystem } from './useProjectileSystem'
import { CombatState, CombatEvent, DesyncEntry } from './combat/types'

interface UseCombatOverlayLogicProps {
  onClose: (newState?: PlayerState) => void
  logEndRef: MutableRefObject<HTMLDivElement | null>
  replayEnabled?: boolean
}

export function useCombatOverlayLogic({ onClose, logEndRef, replayEnabled = true }: UseCombatOverlayLogicProps) {
  const { token } = useAuthStore()
  const { bufferedEvents, isBufferedComplete } = useCombatSSEBuffer(token || '')
  const [playhead, setPlayhead] = useState(0)
  const [combatState, setCombatState] = useState<CombatState>({
    playerUnits: [],
    opponentUnits: [],
    combatLog: [],
    isFinished: false,
    victory: null,
    finalState: null,
    synergies: {},
    traits: [],
    opponentInfo: null,
    regenMap: {},
    simTime: 0,
    defeatMessage: undefined,
    combatSummary: undefined
  })
  const combatStateRef = useRef(combatState)

  useEffect(() => {
    combatStateRef.current = combatState
  }, [combatState])
  const [hoveredTrait, setHoveredTrait] = useState<string | null>(null)
  const [showLog, setShowLog] = useState(false)
  const [combatSpeed, setCombatSpeed] = useState(() => {
    const saved = localStorage.getItem('combatSpeed')
    return saved ? parseFloat(saved) : 1
  })
  const [desyncLogs, setDesyncLogs] = useState<DesyncEntry[]>([])
  const [storedGoldBreakdown, setStoredGoldBreakdown] = useState<{ base: number, interest: number, milestone: number, win_bonus: number, total: number } | null>(null)
  const [displayedGoldBreakdown, setDisplayedGoldBreakdown] = useState<{ base: number, interest: number, milestone: number, win_bonus: number, total: number } | null>(null)

  const { spawnProjectile } = useProjectileSystem()
  const spawnProjectileRef = useRef(spawnProjectile)
  const [pendingProjectiles, setPendingProjectiles] = useState(0)
  const [allEventsReplayed, setAllEventsReplayed] = useState(false)
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

  useEffect(() => {
    spawnProjectileRef.current = spawnProjectile
  }, [spawnProjectile])

  const scheduleNextEvent = (currentEvent: CombatEvent, currentPlayhead: number) => {
    const nextEvent = bufferedEvents[currentPlayhead + 1]
    console.log('[scheduleNextEvent] currentPlayhead:', currentPlayhead, 'nextEvent exists:', !!nextEvent, 'bufferedEvents.length:', bufferedEvents.length)
    
    if (!nextEvent) {
      if (isBufferedComplete) {
        console.log('[scheduleNextEvent] No next event but buffering complete, setting allEventsReplayed')
        setAllEventsReplayed(true)
      } else {
        console.log('[scheduleNextEvent] No next event and buffering not complete yet')
      }
      return
    }

    clearReplayTimer()
    const delay = computeDelayMs(currentEvent, nextEvent, combatSpeed, 1)
    console.log('[scheduleNextEvent] Scheduling next event with delay:', delay, 'ms')
    replayTimerRef.current = setTimeout(() => {
      console.log('[scheduleNextEvent TIMEOUT] Advancing playhead from', currentPlayhead, 'to', currentPlayhead + 1)
      // Guard against stale timers if playhead changed elsewhere.
      setPlayhead(prev => (prev === currentPlayhead ? prev + 1 : prev))
    }, delay)
  }

  const pushDesync = (entry: DesyncEntry) => {
    const recent_events = recentEventsRef.current.slice(-25)
    setDesyncLogs(prev => {
      return [{ ...entry, recent_events }, ...prev].slice(0, 200)
    })
  }

  const clearDesyncLogs = () => setDesyncLogs([])

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

    if (playhead >= bufferedEvents.length) {
      console.log('[REPLAY LOOP] Playhead reached end')
      clearReplayTimer()
      return
    }

    const event = bufferedEvents[playhead]

    // If the effect reruns for the same event (e.g. speed slider changes),
    // do NOT reapply state mutation — only reschedule next step timing.
    if (playhead <= lastAppliedPlayheadRef.current) {
      scheduleNextEvent(event, playhead)
      return
    }

    console.log('Applying event:', event.type, 'seq:', event.seq, 'playhead:', playhead)

    // Keep a rolling buffer of recent events for desync diagnostics
    recentEventsRef.current = [...recentEventsRef.current, event].slice(-50)

    // DEBUG: Log all effect-related events
    if (event.type === 'unit_stunned' || event.type === 'damage_over_time_applied' || event.type === 'stat_buff' || event.type === 'effect_expired') {
      console.log(`[EFFECT EVENT] ${event.type} seq=${event.seq}:`, JSON.stringify(event, null, 2))
    }

    // Handle gold income breakdown so UI can display gold notification after replay
    if (event.type === 'gold_income') {
      const breakdown: any = event as any
      setStoredGoldBreakdown({ base: breakdown.base || 0, interest: breakdown.interest || 0, milestone: breakdown.milestone || 0, win_bonus: breakdown.win_bonus || 0, total: breakdown.total || 0 })
    }

    // Apply event
    const currentState = combatStateRef.current

    // DEBUG: Log state BEFORE applying event (only if effects present)
    if (event.type === 'mana_update' && event.unit_id) {
      const unit = event.unit_id.startsWith('opp_')
        ? currentState.opponentUnits.find(u => u.id === event.unit_id)
        : currentState.playerUnits.find(u => u.id === event.unit_id)

      if (unit?.effects && unit.effects.length > 0) {
        console.log(`[STATE DEBUG BEFORE] ${event.type} seq=${event.seq} unit=${event.unit_id} effects:`, unit.effects)
      }
    }

    const newState = applyCombatEvent(currentState, event, { simTime: currentState.simTime })
    lastAppliedPlayheadRef.current = playhead

    // DEBUG: Log state AFTER applying event (only if effects present)
    if (event.type === 'mana_update' && event.unit_id) {
      const unit = event.unit_id.startsWith('opp_')
        ? newState.opponentUnits.find(u => u.id === event.unit_id)
        : newState.playerUnits.find(u => u.id === event.unit_id)

      if (unit?.effects && unit.effects.length > 0) {
        console.log(`[STATE DEBUG AFTER] ${event.type} seq=${event.seq} unit=${event.unit_id} effects:`, unit.effects)
      }
    }
    
    // GUARD: detect unexpected HP restoration (non-heal events that set HP from 0/null -> >0)
    try {
      const relevantId: string | undefined = (event as any).unit_id || (event as any).target_id
      if (relevantId) {
        const oldUnit = relevantId.startsWith('opp_')
          ? currentState.opponentUnits.find(u => u.id === relevantId)
          : currentState.playerUnits.find(u => u.id === relevantId)
        const newUnit = relevantId.startsWith('opp_')
          ? newState.opponentUnits.find(u => u.id === relevantId)
          : newState.playerUnits.find(u => u.id === relevantId)

        const oldHp = oldUnit?.hp
        const newHp = newUnit?.hp

        const healTypes = new Set(['heal', 'unit_heal', 'hp_regen', 'regen_gain'])
        if ((oldHp === 0 || oldHp === null || oldHp === undefined) && typeof newHp === 'number' && newHp > 0 && !healTypes.has(event.type)) {
          console.warn('[HP GUARD] Unexpected HP restoration detected:', { event: { type: event.type, seq: event.seq, id: relevantId }, oldHp, newHp })
          // also push a desync entry for easier capture
          pushDesync({ unit_id: relevantId, unit_name: (event as any).unit_name || '', seq: event.seq, timestamp: event.timestamp, diff: { hp: { ui: oldHp, server: newHp } }, pending_events: [], note: `hp guard: ${event.type}` })
        }
      }
    } catch (err) {
      console.error('[HP GUARD] guard errored', err)
    }
    
    // Handle delayed HP updates for projectile timing
    if (event.type === 'unit_attack' && event.target_id) {
      // CRITICAL: Use authoritative HP from backend, NOT local calculations!
      // The backend already sends target_hp, post_hp, unit_hp with the correct HP value
      // after applying damage with proper defense calculations.

      // Get authoritative HP from backend event (priority order: unit_hp, target_hp, post_hp, new_hp)
      const authoritativeHp = (event as any).unit_hp ?? (event as any).target_hp ?? (event as any).post_hp ?? (event as any).new_hp

      // Calculate shield change from current state
      const targetUnit = event.target_id.startsWith('opp_')
        ? newState.opponentUnits.find(u => u.id === event.target_id)
        : newState.playerUnits.find(u => u.id === event.target_id)

      if (targetUnit && authoritativeHp !== undefined) {
        const shieldAbsorbed = event.shield_absorbed || 0
        const newShield = Math.max(0, (targetUnit.shield || 0) - shieldAbsorbed)

        // CRITICAL FIX: DO NOT store pending updates or override authoritative state!
        // applyCombatEvent already set the correct HP. No need for delayed updates.
      }
    }
    
    // CRITICAL: Log effects BEFORE setState to verify mutation safety (only if effects present)
    if (event.unit_id) {
      const unit = event.unit_id.startsWith('opp_')
        ? newState.opponentUnits.find(u => u.id === event.unit_id)
        : newState.playerUnits.find(u => u.id === event.unit_id)

      // Only log if unit has effects to reduce console spam
      if (unit?.effects && unit.effects.length > 0) {
        console.log(`[MUTATION CHECK] Before setState: unit=${event.unit_id} effects:`, JSON.parse(JSON.stringify(unit.effects)))
      }
    }

    setCombatState(newState)
    combatStateRef.current = newState

    // CRITICAL: Log effects AFTER setState to check for mutation (only if effects present)
    if (event.unit_id) {
      const unit = event.unit_id.startsWith('opp_')
        ? newState.opponentUnits.find(u => u.id === event.unit_id)
        : newState.playerUnits.find(u => u.id === event.unit_id)

      // Only log if unit has effects to reduce console spam
      if (unit?.effects && unit.effects.length > 0) {
        console.log(`[MUTATION CHECK] After setState: unit=${event.unit_id} effects:`, JSON.parse(JSON.stringify(unit.effects)))
      }
    }

    // Trigger projectile VFX for animation_start events
    if (event.type === 'animation_start' && event.attacker_id && event.target_id) {
      const emoji = '🗡️'
      setPendingProjectiles(p => p + 1)
      spawnProjectileRef.current({ 
        fromId: event.attacker_id, 
        toId: event.target_id, 
        emoji,
        duration: (event.duration || 0.3) * 1000, // convert to ms
        onComplete: () => {
          setPendingProjectiles(p => p - 1)
        }
      })
    }

    // Compare with server if game_state present
    if (event.game_state) {
      const stateDesyncs = compareCombatStates(newState, event.game_state, event)
      stateDesyncs.forEach(pushDesync)
      
      // FAIL FAST: Stop replay if desync detected
      if (stateDesyncs.length > 0) {
        console.error(`🛑 Combat stopped at seq=${event.seq} due to ${stateDesyncs.length} desyncs`)
        clearReplayTimer()
        return  // Don't schedule next event
      }
    }

    // Schedule next
    scheduleNextEvent(event, playhead)
  }, [replayEnabled, isBufferedComplete, bufferedEvents, playhead, combatSpeed])

  // Start replay when buffered
  useEffect(() => {
    const justEnabled = replayEnabled && !prevReplayEnabledRef.current
    console.log('[REPLAY INIT] Running. replayEnabled:', replayEnabled, 'justEnabled:', justEnabled, 'bufferedEvents.length:', bufferedEvents.length, 'replayInitialized:', replayInitializedRef.current, 'lastAppliedPlayhead:', lastAppliedPlayheadRef.current)
    prevReplayEnabledRef.current = replayEnabled

    if (!replayEnabled) {
      console.log('[REPLAY INIT] Gate not enabled, skipping')
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
    setPlayhead(0)
  }, [replayEnabled, bufferedEvents])

  useEffect(() => {
    return () => {
      clearReplayTimer()
      replayInitializedRef.current = false
    }
  }, [])

  // Set isFinished when all events replayed and projectiles done
  useEffect(() => {
    if (allEventsReplayed && pendingProjectiles === 0) {
      setCombatState(prev => ({ ...prev, isFinished: true }))
      combatStateRef.current = { ...combatStateRef.current, isFinished: true }
    }
  }, [allEventsReplayed, pendingProjectiles])

  // Regen cleanup only
  // CRITICAL: DO NOT auto-expire effects here! Effects should ONLY be removed when
  // effect_expired events arrive from backend. Auto-expiration causes desyncs because:
  // 1. Client timing may differ from server by a few ms
  // 2. Reverting stat changes (hp, attack, defense) conflicts with authoritative backend values
  // 3. Backend already sends effect_expired events when effects truly expire
  useEffect(() => {
    const t = setInterval(() => {
      const now = Date.now()
      setCombatState(prev => {
        let changed = false
        const newRegenMap = { ...prev.regenMap }
        for (const k of Object.keys(newRegenMap)) {
          if (newRegenMap[k].expiresAt <= now) {
            delete newRegenMap[k]
            changed = true
          }
        }
        if (!changed) return prev

        return { ...prev, regenMap: newRegenMap }
      })
    }, 500)
    return () => clearInterval(t)
  }, [])

  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [combatState.combatLog])

  const handleClose = () => onClose(combatState.finalState || undefined)
  const handleGoldDismiss = () => { setDisplayedGoldBreakdown(null); setStoredGoldBreakdown(null); handleClose() }

  const hasCombatInitData =
    combatState.playerUnits.length > 0 ||
    combatState.opponentUnits.length > 0 ||
    !!combatState.opponentInfo

  const isSearchingOpponent = !hasCombatInitData && bufferedEvents.length === 0 && !isBufferedComplete

  return {
    playerUnits: combatState.playerUnits,
    opponentUnits: combatState.opponentUnits,
    combatLog: combatState.combatLog,
    isFinished: combatState.isFinished,
    victory: combatState.victory,
    finalState: combatState.finalState,
    synergies: combatState.synergies,
    traits: combatState.traits,
    hoveredTrait,
    setHoveredTrait,
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
    activeAttackerId: combatState.combatSummary?.focus?.attacker_id ?? null,
    activeTargetId: combatState.combatSummary?.focus?.target_id ?? null,
    desyncLogs,
    clearDesyncLogs,
    exportDesyncJSON,
    isSearchingOpponent
  }
}
