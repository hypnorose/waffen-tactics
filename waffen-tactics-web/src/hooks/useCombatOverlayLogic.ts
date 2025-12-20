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
  const [pendingHpUpdates, setPendingHpUpdates] = useState<Record<string, { hp: number, shield: number }>>({})

  const { spawnProjectile } = useProjectileSystem()

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

    // Handle gold income breakdown so UI can display gold notification after replay
    if (event.type === 'gold_income') {
      const breakdown: any = event as any
      setStoredGoldBreakdown({ base: breakdown.base || 0, interest: breakdown.interest || 0, milestone: breakdown.milestone || 0, win_bonus: breakdown.win_bonus || 0, total: breakdown.total || 0 })
    }

    // Apply event
    const currentState = combatStateRef.current
    const newState = applyCombatEvent(currentState, event, { overwriteSnapshots, simTime: currentState.simTime })
    
    // Handle delayed HP updates for projectile timing
    if (event.type === 'unit_attack' && event.target_id && event.damage !== undefined) {
      const shieldAbsorbed = event.shield_absorbed || 0
      const hpDamage = event.damage - shieldAbsorbed
      
      // Find the target unit in current state
      const targetUnit = event.target_id.startsWith('opp_') 
        ? currentState.opponentUnits.find(u => u.id === event.target_id)
        : currentState.playerUnits.find(u => u.id === event.target_id)
      
      if (targetUnit) {
        const oldHp = targetUnit.hp
        const oldShield = targetUnit.shield || 0
        const newHp = Math.max(0, oldHp - hpDamage)
        const newShield = Math.max(0, oldShield - shieldAbsorbed)
        
        // Store pending update
        setPendingHpUpdates(prev => ({
          ...prev,
          [event.target_id!]: { hp: newHp, shield: newShield }
        }))
        
        // Temporarily keep old values in UI state
        if (event.target_id.startsWith('opp_')) {
          newState.opponentUnits = newState.opponentUnits.map(u => 
            u.id === event.target_id ? { ...u, hp: oldHp, shield: oldShield } : u
          )
        } else {
          newState.playerUnits = newState.playerUnits.map(u => 
            u.id === event.target_id ? { ...u, hp: oldHp, shield: oldShield } : u
          )
        }
      }
    }
    
    setCombatState(newState)
    combatStateRef.current = newState

    // Trigger projectile VFX for attacks (replaces old card shake / flashes)
    if (event.type === 'unit_attack' && event.attacker_id && event.target_id) {
      const emoji = event.is_skill ? '✨' : '🗡️'
      spawnProjectile({ 
        fromId: event.attacker_id, 
        toId: event.target_id, 
        emoji,
        onComplete: () => {
          // Apply pending HP update and trigger hurt effect when projectile arrives
          // Skip if combat has finished to prevent overwriting final state
          if (combatStateRef.current.isFinished) return
          
          if (event.target_id && pendingHpUpdates[event.target_id]) {
            setCombatState(prevState => {
              const updatedState = { ...prevState }
              if (event.target_id!.startsWith('opp_')) {
                updatedState.opponentUnits = prevState.opponentUnits.map(u => 
                  u.id === event.target_id ? { ...u, ...pendingHpUpdates[event.target_id] } : u
                )
              } else {
                updatedState.playerUnits = prevState.playerUnits.map(u => 
                  u.id === event.target_id ? { ...u, ...pendingHpUpdates[event.target_id] } : u
                )
              }
              return updatedState
            })
            
            // Clean up pending update
            setPendingHpUpdates(prev => {
              const newPending = { ...prev }
              delete newPending[event.target_id!]
              return newPending
            })
          }
        }
      })
    }

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
      // Finished
      setCombatState(prev => ({ ...prev, isFinished: true }))
      combatStateRef.current = { ...combatStateRef.current, isFinished: true }
    }
  }, [isBufferedComplete, bufferedEvents, playhead, combatSpeed, overwriteSnapshots, spawnProjectile])

  // Start replay when buffered
  useEffect(() => {
    if (isBufferedComplete && bufferedEvents.length > 0) {
      setPlayhead(0)
    }
  }, [isBufferedComplete, bufferedEvents.length])

  // Regen and effect cleanup
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

      // Cleanup expired effects and revert changes
      setCombatState(prev => {
        let changed = false
        const newPlayerUnits = prev.playerUnits.map(u => {
          if (!u.effects || u.effects.length === 0) return u
          const activeEffects = []
          let revertedHp = 0
          let revertedAttack = 0
          let revertedDefense = 0
          let revertedShield = 0
          for (const e of u.effects) {
            if (e.expiresAt && e.expiresAt <= now) {
              // Revert
              if (e.type === 'buff' && e.applied_delta) {
                if (e.stat === 'hp') revertedHp -= e.applied_delta
                else if (e.stat === 'attack') revertedAttack -= e.applied_delta
                else if (e.stat === 'defense') revertedDefense -= e.applied_delta
              } else if (e.type === 'shield' && e.applied_amount) {
                revertedShield -= e.applied_amount
              }
            } else {
              activeEffects.push(e)
            }
          }
          if (activeEffects.length !== u.effects.length) {
            changed = true
            return {
              ...u,
              effects: activeEffects,
              hp: Math.max(0, u.hp + revertedHp),
              attack: u.attack + revertedAttack,
              defense: (u.defense ?? 0) + revertedDefense,
              buffed_stats: {
                ...u.buffed_stats,
                attack: (u.buffed_stats?.attack ?? u.attack) + revertedAttack,
                defense: (u.buffed_stats?.defense ?? u.defense ?? 0) + revertedDefense
              },
              shield: Math.max(0, (u.shield ?? 0) + revertedShield)
            }
          }
          return u
        })
        const newOpponentUnits = prev.opponentUnits.map(u => {
          if (!u.effects || u.effects.length === 0) return u
          const activeEffects = []
          let revertedHp = 0
          let revertedAttack = 0
          let revertedDefense = 0
          let revertedShield = 0
          for (const e of u.effects) {
            if (e.expiresAt && e.expiresAt <= now) {
              // Revert
              if (e.type === 'buff' && e.applied_delta) {
                if (e.stat === 'hp') revertedHp -= e.applied_delta
                else if (e.stat === 'attack') revertedAttack -= e.applied_delta
                else if (e.stat === 'defense') revertedDefense -= e.applied_delta
              } else if (e.type === 'shield' && e.applied_amount) {
                revertedShield -= e.applied_amount
              }
            } else {
              activeEffects.push(e)
            }
          }
          if (activeEffects.length !== u.effects.length) {
            changed = true
            return {
              ...u,
              effects: activeEffects,
              hp: Math.max(0, u.hp + revertedHp),
              attack: u.attack + revertedAttack,
              defense: (u.defense ?? 0) + revertedDefense,
              buffed_stats: {
                ...u.buffed_stats,
                attack: (u.buffed_stats?.attack ?? u.attack) + revertedAttack,
                defense: (u.buffed_stats?.defense ?? u.defense ?? 0) + revertedDefense
              },
              shield: Math.max(0, (u.shield ?? 0) + revertedShield)
            }
          }
          return u
        })
        if (changed) {
          return { ...prev, playerUnits: newPlayerUnits, opponentUnits: newOpponentUnits }
        }
        return prev
      })
    }, 500)
    return () => clearInterval(t)
  }, [])

  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [combatState.combatLog])

  // Clear pending HP updates when combat finishes to prevent race conditions
  useEffect(() => {
    if (combatState.isFinished) {
      setPendingHpUpdates({})
    }
  }, [combatState.isFinished])

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
