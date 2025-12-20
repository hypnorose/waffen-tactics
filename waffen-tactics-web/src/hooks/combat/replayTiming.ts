import { CombatEvent } from './types'

export function computeDelayMs(curr: CombatEvent, next: CombatEvent | null, combatSpeed: number, animationScale: number): number {
  if (!next) return 0
  const currTs = curr.timestamp ?? 0
  const nextTs = next.timestamp ?? 0
  const deltaSec = Math.max(0, nextTs - currTs)
  // Scale by combatSpeed (higher speed = shorter delay)
  const scaledSec = deltaSec / combatSpeed
  // Apply animation scale (e.g., 1.25 to slow animations slightly)
  const finalSec = scaledSec * animationScale
  return Math.max(0, finalSec * 1000) // to ms, min 0
}