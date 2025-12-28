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
}

export function useCombatOverlayLogic({ onClose, logEndRef }: UseCombatOverlayLogicProps) {
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
    defeatMessage: undefined
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
  const [overwriteSnapshots, setOverwriteSnapshots] = useState<boolean>(() => {
    try {
      const v = localStorage.getItem('combat.overwriteSnapshots')
      return v === null ? false : v === 'true'  // Changed default from true to false (Phase 1 makes snapshots accurate)
    } catch (err) {
      return false  // Changed default from true to false
    }
  })
  const [storedGoldBreakdown, setStoredGoldBreakdown] = useState<{ base: number, interest: number, milestone: number, win_bonus: number, total: number } | null>(null)
  const [displayedGoldBreakdown, setDisplayedGoldBreakdown] = useState<{ base: number, interest: number, milestone: number, win_bonus: number, total: number } | null>(null)

  const { spawnProjectile } = useProjectileSystem()
  const [pendingProjectiles, setPendingProjectiles] = useState(0)
  const [allEventsReplayed, setAllEventsReplayed] = useState(false)

  const pushDesync = (entry: DesyncEntry) => {
    setDesyncLogs(prev => [entry, ...prev].slice(0, 200))
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
      localStorage.setItem('combat.overwriteSnapshots', overwriteSnapshots ? 'true' : 'false')
    } catch (err) {}
  }, [overwriteSnapshots])

  useEffect(() => {
    try {
      localStorage.setItem('combatSpeed', combatSpeed.toString())
    } catch (err) {}
  }, [combatSpeed])

  // Replay loop
  useEffect(() => {
    if (!isBufferedComplete || playhead >= bufferedEvents.length) return

    const event = bufferedEvents[playhead]
    console.log('Applying event:', event.type, 'seq:', event.seq, 'playhead:', playhead)

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

    const newState = applyCombatEvent(currentState, event, { overwriteSnapshots, simTime: currentState.simTime })

    // DEBUG: Log state AFTER applying event (only if effects present)
    if (event.type === 'mana_update' && event.unit_id) {
      const unit = event.unit_id.startsWith('opp_')
        ? newState.opponentUnits.find(u => u.id === event.unit_id)
        : newState.playerUnits.find(u => u.id === event.unit_id)

      if (unit?.effects && unit.effects.length > 0) {
        console.log(`[STATE DEBUG AFTER] ${event.type} seq=${event.seq} unit=${event.unit_id} effects:`, unit.effects)
      }
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
      const emoji = event.animation_id === 'skill_attack' ? '⚡' : '🗡️'
      setPendingProjectiles(p => p + 1)
      spawnProjectile({ 
        fromId: event.attacker_id, 
        toId: event.target_id, 
        emoji,
        duration: (event.duration || 0.3) * 1000, // convert to ms
        onComplete: () => {
          setPendingProjectiles(p => p - 1)
        }
      })
    }

    // NOTE: Projectile VFX now triggered by animation_start events above
    // Keeping unit_attack trigger commented for reference
    /*
    if (event.type === 'unit_attack' && event.attacker_id && event.target_id) {
      const emoji = event.is_skill ? '⚡' : '🗡️'
      setPendingProjectiles(p => p + 1)
      spawnProjectile({ 
        fromId: event.attacker_id, 
        toId: event.target_id, 
        emoji,
        onComplete: () => {
          setPendingProjectiles(p => p - 1)
        }
      })
    }
    */

    // Compare with server if game_state present
    if (event.game_state) {
      const stateDesyncs = compareCombatStates(newState, event.game_state, event)
      stateDesyncs.forEach(pushDesync)
    }

    // Schedule next
    const nextEvent = bufferedEvents[playhead + 1]
    if (nextEvent) {
      const delay = computeDelayMs(event, nextEvent, combatSpeed, 1)
      setTimeout(() => setPlayhead(playhead + 1), delay)
    } else {
      // All events have been replayed
      setAllEventsReplayed(true)
    }
  }, [isBufferedComplete, bufferedEvents, playhead, combatSpeed, overwriteSnapshots, spawnProjectile])

  // Start replay when buffered
  useEffect(() => {
    if (isBufferedComplete && bufferedEvents.length > 0) {
      setPlayhead(0)
    }
  }, [isBufferedComplete, bufferedEvents.length])

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
    desyncLogs,
    clearDesyncLogs,
    exportDesyncJSON,
    overwriteSnapshots,
    setOverwriteSnapshots
  }
}
