import { useState, useRef, useEffect, useCallback } from 'react'
import { CombatEvent } from './types'

export function useCombatAnimations() {
  const [attackingUnits, setAttackingUnits] = useState<string[]>([])
  const [targetUnits, setTargetUnits] = useState<string[]>([])
  const [animatingUnits, setAnimatingUnits] = useState<string[]>([])
  const [skillUnits, setSkillUnits] = useState<string[]>([])
  const [attackDurations, setAttackDurations] = useState<Record<string, number>>({})
  const activeTimeoutsRef = useRef<number[]>([])
  const animationScale = 1

  const triggerAttackAnimation = useCallback((attacker: string, target: string, combatSpeed: number, allUnits: any[]) => {
    setAttackingUnits(prev => [...prev, attacker])
    setTargetUnits(prev => [...prev, target])
    setAnimatingUnits(prev => [...prev, attacker, target])

    const attackerUnit = allUnits.find(u => u.id === attacker)
    const attackerAS = (attackerUnit && attackerUnit.buffed_stats?.attack_speed) || 1
    const normalizedAS = Math.max(0.1, parseFloat(String(attackerAS)))
    const baseInterval = 1000 / normalizedAS
    const duration = Math.round(Math.max(150, Math.min(3000, baseInterval * animationScale / combatSpeed)))

    setAttackDurations(prev => ({ ...prev, [attacker]: duration, [target]: duration }))

    const id1 = setTimeout(() => {
      setAttackingUnits(prev => prev.filter(id => id !== attacker))
      setAttackDurations(prev => { const copy = { ...prev }; delete copy[attacker]; return copy })
    }, duration)
    activeTimeoutsRef.current.push(id1)

    const id2 = setTimeout(() => {
      setTargetUnits(prev => prev.filter(id => id !== target))
      setAttackDurations(prev => { const copy = { ...prev }; delete copy[target]; return copy })
    }, duration)
    activeTimeoutsRef.current.push(id2)

    const id3 = setTimeout(() => {
      setAnimatingUnits(prev => prev.filter(id => id !== attacker && id !== target))
    }, duration)
    activeTimeoutsRef.current.push(id3)
  }, [])

  const triggerSkillAnimation = useCallback((caster: string, combatSpeed: number, allUnits: any[]) => {
    setSkillUnits(prev => [...prev, caster])
    setAnimatingUnits(prev => [...prev, caster])

    const casterUnit = allUnits.find(u => u.id === caster)
    const casterAS = (casterUnit && casterUnit.buffed_stats?.attack_speed) || 1
    const normalizedAS = Math.max(0.1, parseFloat(String(casterAS)))
    const baseInterval = 1000 / normalizedAS
    const duration = Math.round(Math.max(150, Math.min(3000, baseInterval * animationScale / combatSpeed)))

    setAttackDurations(prev => ({ ...prev, [caster]: duration }))

    const id1 = setTimeout(() => {
      setSkillUnits(prev => prev.filter(id => id !== caster))
      setAttackDurations(prev => { const copy = { ...prev }; delete copy[caster]; return copy })
    }, duration)
    activeTimeoutsRef.current.push(id1)

    const id2 = setTimeout(() => {
      setAnimatingUnits(prev => prev.filter(id => id !== caster))
    }, duration)
    activeTimeoutsRef.current.push(id2)
  }, [])

  const triggerTargetFlash = useCallback((unitId: string, combatSpeed: number) => {
    setTargetUnits(prev => [...prev, unitId])
    const dur = Math.round(600 * animationScale / combatSpeed)
    const id = setTimeout(() => setTargetUnits(prev => prev.filter(id => id !== unitId)), dur)
    activeTimeoutsRef.current.push(id)
  }, [])

  useEffect(() => {
    return () => {
      activeTimeoutsRef.current.forEach(id => clearTimeout(id))
      activeTimeoutsRef.current = []
    }
  }, [])

  return {
    attackingUnits,
    targetUnits,
    animatingUnits,
    skillUnits,
    attackDurations,
    triggerAttackAnimation,
    triggerSkillAnimation,
    triggerTargetFlash
  }
}