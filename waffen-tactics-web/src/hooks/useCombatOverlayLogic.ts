// Kopia logiki z CombatOverlay.tsx do refaktoryzacji

import { useState, useEffect, useRef } from 'react'
import { PlayerState } from '../store/gameStore'
import { useAuthStore } from '../store/authStore'

interface Unit {
  id: string
  name: string
  hp: number
  max_hp: number
  attack: number
  star_level: number
  cost?: number
  factions?: string[]
  classes?: string[]
  buffed_stats?: {
    hp?: number
    attack?: number
    defense?: number
    attack_speed?: number
    max_mana?: number
  }
}

interface TraitDefinition {
  name: string
  type: string
  thresholds: number[]
  effects: any[]
}

interface CombatEvent {
  type: string
  message?: string
  player_units?: Unit[]
  opponent_units?: Unit[]
  synergies?: Record<string, {count: number, tier: number}>
  traits?: TraitDefinition[]
  opponent?: {name: string, wins: number, level: number}
  attacker_id?: string
  target_id?: string
  damage?: number
  unit_hp?: number
  target_hp?: number
  target_max_hp?: number
  unit_id?: string
  round?: number
  state?: PlayerState
  amount_per_sec?: number
  total_amount?: number
  duration?: number
  timestamp?: number
}


import { MutableRefObject } from 'react'

interface UseCombatOverlayLogicProps {
  onClose: (newState?: PlayerState) => void
  logEndRef: MutableRefObject<HTMLDivElement | null>
}

export function useCombatOverlayLogic({ onClose, logEndRef }: UseCombatOverlayLogicProps) {
  const { token } = useAuthStore()
  const [playerUnits, setPlayerUnits] = useState<Unit[]>([])
  const [opponentUnits, setOpponentUnits] = useState<Unit[]>([])
  const [combatLog, setCombatLog] = useState<string[]>([])
  const [isFinished, setIsFinished] = useState(false)
  const [finalState, setFinalState] = useState<PlayerState | null>(null)
  const [synergies, setSynergies] = useState<Record<string, {count: number, tier: number}>>({})
  const [hoveredTrait, setHoveredTrait] = useState<string | null>(null)
  const [opponentInfo, setOpponentInfo] = useState<{name: string, wins: number, level: number} | null>(null)
  const [showLog, setShowLog] = useState(false)
  const [attackingUnit, setAttackingUnit] = useState<string | null>(null)
  const [targetUnit, setTargetUnit] = useState<string | null>(null)
  const [combatSpeed, setCombatSpeed] = useState(() => {
    const saved = localStorage.getItem('combatSpeed')
    return saved ? parseFloat(saved) : 1
  })
  const [eventQueue, setEventQueue] = useState<CombatEvent[]>([])
  const [regenMap, setRegenMap] = useState<Record<string, { amount_per_sec: number; total_amount: number; expiresAt: number }>>({})
  const [isPlaying, setIsPlaying] = useState(false)
  const [storedGoldBreakdown, setStoredGoldBreakdown] = useState<{base: number, interest: number, milestone: number, win_bonus: number, total: number} | null>(null)
  const [displayedGoldBreakdown, setDisplayedGoldBreakdown] = useState<{base: number, interest: number, milestone: number, win_bonus: number, total: number} | null>(null)
  // Fix: lastTimestampRef must be at top level, not inside useEffect
  const lastTimestampRef = useRef<number | null>(null)

  useEffect(() => {
    if (!token) {
      console.error('No token found!')
      setCombatLog(['❌ Brak tokenu - zaloguj się ponownie'])
      setIsFinished(true)
      return
    }

    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const eventSource = new EventSource(`${API_URL}/game/combat?token=${encodeURIComponent(token)}`)

    eventSource.onopen = () => console.log('EventSource connected')
    eventSource.onmessage = (event) => {
      try {
        const data: CombatEvent = JSON.parse(event.data)
        setEventQueue(prev => [...prev, data])
        if (data.type === 'units_init') setIsPlaying(true)
        if (data.type === 'end') eventSource.close()
      } catch (err) {
        console.error('Error parsing combat event', err)
      }
    }
    eventSource.onerror = (err) => {
      console.error('EventSource error', err)
      if (eventSource.readyState === EventSource.CLOSED) eventSource.close()
    }
    return () => eventSource.close()
  }, [token])

  useEffect(() => {
    if (!isPlaying || eventQueue.length === 0) return;

    const processNextEvent = () => {
      setEventQueue(prev => {
        if (prev.length === 0) return prev;
        const [nextEvent, ...rest] = prev;
        // Update lastTimestampRef for delay calculation
        let eventTimestamp = typeof nextEvent.timestamp === 'number' ? nextEvent.timestamp : null;
        if (eventTimestamp !== null) lastTimestampRef.current = eventTimestamp;

        if (nextEvent.type === 'units_init') {
          if (nextEvent.player_units) setPlayerUnits(nextEvent.player_units);
          if (nextEvent.opponent_units) setOpponentUnits(nextEvent.opponent_units);
          if (nextEvent.synergies) setSynergies(nextEvent.synergies);
          if (nextEvent.opponent) setOpponentInfo(nextEvent.opponent);
        } else if (nextEvent.type === 'unit_attack') {
          if (nextEvent.attacker_id && nextEvent.target_id) {
            setAttackingUnit(nextEvent.attacker_id);
            setTargetUnit(nextEvent.target_id);
            setTimeout(() => { setAttackingUnit(null); setTargetUnit(null); }, 1500 / combatSpeed);
          }
          // Accept both unit_hp (preferred) and target_hp (legacy/backend)
          const attackHp = nextEvent.unit_hp !== undefined ? nextEvent.unit_hp : nextEvent.target_hp;
          if (nextEvent.target_id && attackHp !== undefined) {
            if (nextEvent.target_id.startsWith('opp_')) setOpponentUnits(prev => prev.map(u => u.id === nextEvent.target_id ? { ...u, hp: attackHp } : u));
            else setPlayerUnits(prev => prev.map(u => u.id === nextEvent.target_id ? { ...u, hp: attackHp } : u));
          }
        } else if (nextEvent.type === 'gold_income') {
          const breakdown = nextEvent as any;
          setStoredGoldBreakdown({ base: breakdown.base || 0, interest: breakdown.interest || 0, milestone: breakdown.milestone || 0, win_bonus: breakdown.win_bonus || 0, total: breakdown.total || 0 });
        } else if (nextEvent.type === 'end') {
          setIsFinished(true);
          if (nextEvent.state) setFinalState(nextEvent.state);
          setIsPlaying(false);
        } else if (nextEvent.type === 'unit_heal') {
          // Accept both unit_hp (preferred) and target_hp (legacy/backend)
          const healedHp = nextEvent.unit_hp !== undefined ? nextEvent.unit_hp : nextEvent.target_hp;
          if (nextEvent.unit_id && healedHp !== undefined) {
            if (nextEvent.unit_id.startsWith('opp_')) {
              setOpponentUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? { ...u, hp: healedHp } : u));
            } else {
              setPlayerUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? { ...u, hp: healedHp } : u));
            }
          }
        } else if (nextEvent.type === 'regen_gain') {
          if (nextEvent.unit_id) {
            const dur = nextEvent.duration || 5;
            const expiresAt = Date.now() + dur * 1000;
            setRegenMap(prev => ({ ...prev, [nextEvent.unit_id!]: { amount_per_sec: nextEvent.amount_per_sec || 0, total_amount: nextEvent.total_amount || 0, expiresAt } }));
            const readable = `💚 ${nextEvent.unit_id} gains ${Math.round((nextEvent.total_amount || 0))} HP over ${dur}s`;
            setCombatLog(prev => [...prev, readable]);
          }
        }
        if (nextEvent.message) setCombatLog(prev => [...prev, nextEvent.message!]);
        return rest;
      });
    };

    // Calculate delay based on timestamp difference
    let delay = 100 / combatSpeed; // fallback minimal delay
    if (eventQueue.length > 1) {
      const curr = typeof eventQueue[0].timestamp === 'number' ? eventQueue[0].timestamp : null;
      const next = typeof eventQueue[1].timestamp === 'number' ? eventQueue[1].timestamp : null;
      if (curr !== null && next !== null && next > curr) {
        delay = ((next - curr) * 1000) / combatSpeed;
      }
    }
    const timer = setTimeout(processNextEvent, delay);
    return () => clearTimeout(timer);
  }, [eventQueue, isPlaying, combatSpeed]);

  useEffect(() => {
    const t = setInterval(() => {
      const now = Date.now()
      setRegenMap(prev => {
        const copy = { ...prev }
        let changed = false
        for (const k of Object.keys(copy)) {
          if (copy[k].expiresAt <= now) {
            delete copy[k]
            changed = true
          }
        }
        return changed ? copy : prev
      })
    }, 500)
    return () => clearInterval(t)
  }, [])

  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [combatLog])

  const handleClose = () => onClose(finalState || undefined)
  const handleGoldDismiss = () => { setDisplayedGoldBreakdown(null); setStoredGoldBreakdown(null); handleClose() }

  return {
    playerUnits,
    opponentUnits,
    combatLog,
    isFinished,
    finalState,
    synergies,
    hoveredTrait,
    setHoveredTrait,
    opponentInfo,
    showLog,
    setShowLog,
    attackingUnit,
    targetUnit,
    combatSpeed,
    setCombatSpeed,
    regenMap,
    storedGoldBreakdown,
    displayedGoldBreakdown,
    setDisplayedGoldBreakdown,
    setStoredGoldBreakdown,
    handleClose,
    handleGoldDismiss
  }
}
