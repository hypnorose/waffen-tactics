import { useEffect, useState } from 'react'

export type CombatMatchmakingPhase = 'searching' | 'final' | 'done'

export const COMBAT_ROULETTE_CANDIDATES = [
  'Uszaty Cwel',
  'Słonik Dumbo',
  'Srebrny Baron',
  'Spijacz kropelek',
  'Spermofil pospolity',
  'Przyprawowy Imperator',
  'Giełdowy Dyletant',
  'Obwoźny sprzedawca oprawek',
  'Grochowianin nr. 207',
  'Skurwiel z Wesołej',
] as const

/**
 * Owns only the deterministic intro timing and replay gate. Combat state and
 * replay reduction remain in useCombatOverlayLogic.
 */
export function useCombatMatchmakingFlow() {
  const [rouletteIndex, setRouletteIndex] = useState(0)
  const [matchmakingPhase, setMatchmakingPhase] = useState<CombatMatchmakingPhase>('searching')
  const [replayGateOpen, setReplayGateOpen] = useState(false)

  useEffect(() => {
    const rouletteTimer = setTimeout(() => setMatchmakingPhase('final'), 2000)
    const finalTimer = setTimeout(() => setMatchmakingPhase('done'), 3000)
    return () => {
      clearTimeout(rouletteTimer)
      clearTimeout(finalTimer)
    }
  }, [])

  useEffect(() => {
    if (matchmakingPhase !== 'searching') return
    const interval = setInterval(() => {
      setRouletteIndex(prev => (prev + 1) % COMBAT_ROULETTE_CANDIDATES.length)
    }, 320)
    return () => clearInterval(interval)
  }, [matchmakingPhase])

  const showMatchmakingOverlay = matchmakingPhase !== 'done'

  useEffect(() => {
    // Replay starts only after matchmaking/intro panel is fully dismissed.
    setReplayGateOpen(!showMatchmakingOverlay)
  }, [showMatchmakingOverlay])

  return {
    matchmakingPhase,
    rouletteCandidate: COMBAT_ROULETTE_CANDIDATES[rouletteIndex],
    showMatchmakingOverlay,
    replayGateOpen,
  }
}
