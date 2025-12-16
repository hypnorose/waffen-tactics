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
  defense?: number
  star_level: number
  cost?: number
  factions?: string[]
  classes?: string[]
  position?: string
  buffed_stats?: {
    hp?: number
    attack?: number
    defense?: number
    attack_speed?: number
    max_mana?: number
  }
  current_mana?: number
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
  // Mana and skill casting events
  caster_id?: string
  caster_name?: string
  skill_name?: string
  current_mana?: number
  max_mana?: number
  // Additional properties for various events
  attacker_name?: string
  target_name?: string
  unit_name?: string
  amount?: number
  stat?: string
 side?: string
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
  const [victory, setVictory] = useState<boolean | null>(null) // null = ongoing, true = win, false = lose
  const [finalState, setFinalState] = useState<PlayerState | null>(null)
  const [synergies, setSynergies] = useState<Record<string, {count: number, tier: number}>>({})
  const [traits, setTraits] = useState<TraitDefinition[]>([])
  const [hoveredTrait, setHoveredTrait] = useState<string | null>(null)
  const [opponentInfo, setOpponentInfo] = useState<{name: string, wins: number, level: number} | null>(null)
  const [showLog, setShowLog] = useState(false)
  // Support multiple concurrent attack/target highlights so events don't cancel each other
  const [attackingUnits, setAttackingUnits] = useState<string[]>([])
  const [targetUnits, setTargetUnits] = useState<string[]>([])
  const [combatSpeed, setCombatSpeed] = useState(() => {
    const saved = localStorage.getItem('combatSpeed')
    return saved ? parseFloat(saved) : 1
  })
  const [eventQueue, setEventQueue] = useState<CombatEvent[]>([])
  const [animatingUnits, setAnimatingUnits] = useState<string[]>([])
  // Make animations slightly slower by default but scale with combatSpeed
  // animationScale > 1 slows animations; follow-up divides by combatSpeed
  const animationScale = 1.25
  const [regenMap, setRegenMap] = useState<Record<string, { amount_per_sec: number; total_amount: number; expiresAt: number }>>({})
  const [isPlaying, setIsPlaying] = useState(false)
  const [storedGoldBreakdown, setStoredGoldBreakdown] = useState<{base: number, interest: number, milestone: number, win_bonus: number, total: number} | null>(null)
  const [displayedGoldBreakdown, setDisplayedGoldBreakdown] = useState<{base: number, interest: number, milestone: number, win_bonus: number, total: number} | null>(null)
  // Fix: lastTimestampRef must be at top level, not inside useEffect
  const lastTimestampRef = useRef<number | null>(null)

  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    // Prevent multiple EventSources
    if (eventSourceRef.current) {
      return
    }
    
    if (!token) {
      console.error('No token found!')
      setCombatLog(['❌ Brak tokenu - zaloguj się ponownie'])
      setIsFinished(true)
      return
    }

    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const eventSource = new EventSource(`${API_URL}/game/combat?token=${encodeURIComponent(token)}`)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => console.log('EventSource connected')
    eventSource.onmessage = (event) => {
      try {
        const data: CombatEvent = JSON.parse(event.data)
        setEventQueue(prev => [...prev, data])
        if (data.type === 'units_init') setIsPlaying(true)
        if (data.type === 'end') {
          eventSource.close()
          eventSourceRef.current = null
        }
      } catch (err) {
        console.error('Error parsing combat event', err)
      }
    }
    eventSource.onerror = (err) => {
      console.error('EventSource error', err)
      if (eventSource.readyState === EventSource.CLOSED) {
        eventSource.close()
        eventSourceRef.current = null
      }
    }
    return () => {
      eventSource.close()
      eventSourceRef.current = null
    }
  }, []) // Remove token dependency since it shouldn't change during combat

  useEffect(() => {
    if (!isPlaying || eventQueue.length === 0) return;

    const processNextEvent = () => {
      setEventQueue(prev => {
        if (prev.length === 0) return prev;
        const [nextEvent, ...rest] = prev;
        // Update lastTimestampRef for delay calculation
        let eventTimestamp = typeof nextEvent.timestamp === 'number' ? nextEvent.timestamp : null;
        if (eventTimestamp !== null) lastTimestampRef.current = eventTimestamp;

        if (nextEvent.type === 'start') {
          const msg = '⚔️ Walka rozpoczyna się!'
          setCombatLog(prev => [...prev, msg]);
        } else if (nextEvent.type === 'units_init') {
          if (nextEvent.player_units) setPlayerUnits(nextEvent.player_units.map(u => ({ ...u, current_mana: u.current_mana ?? 0 })));
          if (nextEvent.opponent_units) setOpponentUnits(nextEvent.opponent_units.map(u => ({ ...u, current_mana: u.current_mana ?? 0 })));
          if (nextEvent.synergies) setSynergies(nextEvent.synergies);
          if (nextEvent.traits) setTraits(nextEvent.traits);
          if (nextEvent.opponent) setOpponentInfo(nextEvent.opponent);
        } else if (nextEvent.type === 'unit_attack') {
          if (nextEvent.attacker_id && nextEvent.target_id) {
            const attacker = nextEvent.attacker_id
            const target = nextEvent.target_id
            // add attacker/target to active lists so animations can overlap
            setAttackingUnits(prev => [...prev, attacker])
            setTargetUnits(prev => [...prev, target])
            setAnimatingUnits(prev => [...prev, attacker, target])
            const duration = Math.round(1500 * animationScale / combatSpeed)
            setTimeout(() => { setAttackingUnits(prev => prev.filter(id => id !== attacker)) }, duration)
            setTimeout(() => { setTargetUnits(prev => prev.filter(id => id !== target)) }, duration)
            setTimeout(() => { setAnimatingUnits(prev => prev.filter(id => id !== attacker && id !== target)) }, duration)
          }
          // Accept both unit_hp (preferred) and target_hp (legacy/backend)
          const attackHp = nextEvent.unit_hp !== undefined ? nextEvent.unit_hp : nextEvent.target_hp;
          if (nextEvent.target_id && attackHp !== undefined) {
            if (nextEvent.target_id.startsWith('opp_')) setOpponentUnits(prev => prev.map(u => u.id === nextEvent.target_id ? { ...u, hp: attackHp } : u));
            else setPlayerUnits(prev => prev.map(u => u.id === nextEvent.target_id ? { ...u, hp: attackHp } : u));
          }
          const msg = `⚔️ ${nextEvent.attacker_name} atakuje ${nextEvent.target_name} (${(nextEvent.damage ?? 0).toFixed(2)} dmg)`
          setCombatLog(prev => [...prev, msg]);
        } else if (nextEvent.type === 'unit_died') {
          // Ensure HP is 0 when unit dies
          if (nextEvent.unit_id) {
            if (nextEvent.unit_id.startsWith('opp_')) {
              setOpponentUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? { ...u, hp: 0 } : u));
            } else {
              setPlayerUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? { ...u, hp: 0 } : u));
            }
          }
          const msg = `💀 ${nextEvent.unit_name} zostaje pokonany!`
          setCombatLog(prev => [...prev, msg]);
        } else if (nextEvent.type === 'gold_reward') {
          const msg = `💰 ${nextEvent.unit_name} daje +${nextEvent.amount} gold (sojusznik umarł)`
          setCombatLog(prev => [...prev, msg]);
        } else if (nextEvent.type === 'stat_buff') {
          console.log('Received stat_buff event:', nextEvent);
          const statName = nextEvent.stat === 'attack' ? 'Ataku' : nextEvent.stat === 'defense' ? 'Obrony' : nextEvent.stat || 'Statystyki';
          const msg = `⬆️ ${nextEvent.unit_name} zyskuje +${nextEvent.amount} ${statName} (zabity wróg)`
          setCombatLog(prev => [...prev, msg]);
          // Update unit buffed_stats in UI
          if (nextEvent.unit_id) {
            const updateUnit = (u: Unit) => {
              if (nextEvent.stat === 'attack') {
                const currentAttack = u.buffed_stats?.attack ?? u.attack;
                return { ...u, buffed_stats: { ...u.buffed_stats, attack: currentAttack + (nextEvent.amount ?? 0) } };
              } else if (nextEvent.stat === 'defense') {
                const currentDefense = u.buffed_stats?.defense ?? u.defense ?? 0;
                return { ...u, buffed_stats: { ...u.buffed_stats, defense: currentDefense + (nextEvent.amount ?? 0) } };
              }
              return u;
            };
            if (nextEvent.unit_id.startsWith('opp_')) {
              setOpponentUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? updateUnit(u) : u));
            } else {
              setPlayerUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? updateUnit(u) : u));
            }
          }
        } else if (nextEvent.type === 'gold_income') {
          const breakdown = nextEvent as any;
          setStoredGoldBreakdown({ base: breakdown.base || 0, interest: breakdown.interest || 0, milestone: breakdown.milestone || 0, win_bonus: breakdown.win_bonus || 0, total: breakdown.total || 0 });
        } else if (nextEvent.type === 'victory') {
          const msg = '🎉 ZWYCIĘSTWO!'
          setCombatLog(prev => [...prev, msg]);
          setVictory(true);
        } else if (nextEvent.type === 'defeat') {
          const msg = nextEvent.message || '💔 PRZEGRANA!'
          setCombatLog(prev => [...prev, msg]);
          setVictory(false);
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
          const msg = `💚 ${nextEvent.unit_name} regeneruje ${(nextEvent.amount ?? 0).toFixed(2)} HP`
          setCombatLog(prev => [...prev, msg]);
        } else if (nextEvent.type === 'regen_gain') {
          if (nextEvent.unit_id) {
            const dur = nextEvent.duration || 5;
            const expiresAt = Date.now() + dur * 1000;
            setRegenMap(prev => ({ ...prev, [nextEvent.unit_id!]: { amount_per_sec: nextEvent.amount_per_sec || 0, total_amount: nextEvent.total_amount || 0, expiresAt } }));
            const msg = `💚 ${nextEvent.unit_name} zyskuje +${(nextEvent.total_amount || 0).toFixed(2)} HP przez ${dur}s`
            setCombatLog(prev => [...prev, msg]);
          }
        } else if (nextEvent.type === 'mana_update') {
          if (nextEvent.unit_id && nextEvent.current_mana !== undefined) {
            if (nextEvent.unit_id.startsWith('opp_')) {
              setOpponentUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? { ...u, current_mana: nextEvent.current_mana } : u));
            } else {
              setPlayerUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? { ...u, current_mana: nextEvent.current_mana } : u));
            }
          }
          const msg = `🔮 ${nextEvent.unit_name} mana: ${nextEvent.current_mana}/${nextEvent.max_mana}`
          setCombatLog(prev => [...prev, msg]);
        } else if (nextEvent.type === 'skill_cast') {
          // Update target HP if damage was dealt
          if (nextEvent.target_id && nextEvent.target_hp !== undefined) {
            if (nextEvent.target_id.startsWith('opp_')) {
              setOpponentUnits(prev => prev.map(u => u.id === nextEvent.target_id ? { ...u, hp: nextEvent.target_hp! } : u));
            } else {
              setPlayerUnits(prev => prev.map(u => u.id === nextEvent.target_id ? { ...u, hp: nextEvent.target_hp! } : u));
            }
          }
          const msg = `✨ ${nextEvent.caster_name} używa ${nextEvent.skill_name}!`
          setCombatLog(prev => [...prev, msg]);
        }
        return rest;
      });
    };

    // Calculate delay based on timestamp difference. Use fallback slightly slower
    // than before but scale with combatSpeed and animationScale so the UI feels
    // a bit more readable at normal speeds and still speeds up when user
    // increases combatSpeed.
    let delay = (120 * animationScale) / combatSpeed; // fallback minimal delay (ms)
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
    victory,
    finalState,
    synergies,
    traits,
    hoveredTrait,
    setHoveredTrait,
    opponentInfo,
    showLog,
    setShowLog,
    attackingUnits,
    targetUnits,
    animatingUnits,
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
