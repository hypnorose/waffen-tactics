import { useState, useEffect, useRef, MutableRefObject } from 'react'
import { PlayerState } from '../store/gameStore'
import { useAuthStore } from '../store/authStore'
import { useCombatSSEBuffer } from './combat/useCombatSSEBuffer'
import { computeDelayMs } from './combat/replayTiming'
import { applyCombatEvent } from './combat/applyEvent'
import { compareCombatStates } from './combat/desync'
import { useCombatAnimations } from './combat/useCombatAnimations'
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
      return v === null ? true : v === 'true'
    } catch (err) {
      return true
    }
  })
  const [storedGoldBreakdown, setStoredGoldBreakdown] = useState<{ base: number, interest: number, milestone: number, win_bonus: number, total: number } | null>(null)
  const [displayedGoldBreakdown, setDisplayedGoldBreakdown] = useState<{ base: number, interest: number, milestone: number, win_bonus: number, total: number } | null>(null)

  const { attackingUnits, targetUnits, animatingUnits, skillUnits, attackDurations, triggerAttackAnimation, triggerSkillAnimation, triggerTargetFlash } = useCombatAnimations()

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
    setCombatState(newState)
    combatStateRef.current = newState

    // Trigger animations
    if (event.type === 'unit_attack' && event.attacker_id && event.target_id) {
      const allUnits = [...newState.playerUnits, ...newState.opponentUnits]
      triggerAttackAnimation(event.attacker_id, event.target_id, combatSpeed, allUnits)
    } else if (event.type === 'skill_cast' && event.caster_id) {
      const allUnits = [...newState.playerUnits, ...newState.opponentUnits]
      triggerSkillAnimation(event.caster_id, combatSpeed, allUnits)
    } else if (event.type === 'damage_over_time_tick' && event.unit_id) {
      triggerTargetFlash(event.unit_id, combatSpeed)
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
  }, [isBufferedComplete, bufferedEvents, playhead, combatSpeed, overwriteSnapshots, triggerAttackAnimation, triggerTargetFlash])

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
    attackingUnits,
    targetUnits,
    skillUnits,
    attackDurations,
    animatingUnits,
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
