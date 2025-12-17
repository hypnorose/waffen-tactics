// Kopia logiki z CombatOverlay.tsx do refaktoryzacji

import { useState, useEffect, useRef } from 'react'
import { PlayerState } from '../store/gameStore'
import { useAuthStore } from '../store/authStore'

interface Unit {
  id: string
  name: string
  hp: number
  max_hp: number
  shield?: number
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
  effects?: EffectSummary[]
  persistent_buffs?: Record<string, number>
  avatar?: string
  skill?: any
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
  opponent?: {name: string, wins: number, level: number, avatar?: string}
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
  timestamp?: number
  seq?: number
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
  is_skill?: boolean
  buff_type?: string
  duration?: number
  shield_absorbed?: number
  cause?: string
  ticks?: number
  interval?: number
}

interface EffectSummary {
  id?: string
  type: string
  amount?: number
  stat?: string
  duration?: number
  expiresAt?: number
  ticks?: number
  interval?: number
  damage?: number
  caster_name?: string
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
  const [attackDurations, setAttackDurations] = useState<Record<string, number>>({})
  // Make animations slightly slower by default but scale with combatSpeed
  // animationScale > 1 slows animations; follow-up divides by combatSpeed
  const animationScale = 1.25
  const [regenMap, setRegenMap] = useState<Record<string, { amount_per_sec: number; total_amount: number; expiresAt: number }>>({})
  // Effects will be attached to unit objects as `effects: EffectSummary[]`
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
        // DEBUG: console.log('Processing event:', nextEvent);
        // Update lastTimestampRef for delay calculation
        let eventTimestamp = typeof nextEvent.timestamp === 'number' ? nextEvent.timestamp : null;
        if (eventTimestamp !== null) lastTimestampRef.current = eventTimestamp;

        if (nextEvent.type === 'start') {
          const msg = '⚔️ Walka rozpoczyna się!'
          setCombatLog(prev => [...prev, msg]);
        } else if (nextEvent.type === 'units_init') {
          if (nextEvent.player_units) {
            const players = nextEvent.player_units;
            const normalizedPlayers = players.map((u, idx) => ({
              ...u,
              hp: u.hp ?? 0,
              current_mana: u.current_mana ?? 0,
              shield: u.shield ?? 0,
              position: u.position ?? (idx < Math.ceil(players.length / 2) ? 'front' : 'back')
            }));
            setPlayerUnits(normalizedPlayers);
          }
          if (nextEvent.opponent_units) {
            const opponents = nextEvent.opponent_units;
            const normalizedOpps = opponents.map((u, idx) => ({
              ...u,
              hp: u.hp ?? 0,
              current_mana: u.current_mana ?? 0,
              shield: u.shield ?? 0,
              position: u.position ?? (idx < Math.ceil(opponents.length / 2) ? 'front' : 'back')
            }));
            setOpponentUnits(normalizedOpps);
          }
          if (nextEvent.synergies) setSynergies(nextEvent.synergies);
          if (nextEvent.traits) setTraits(nextEvent.traits);
          if (nextEvent.opponent) setOpponentInfo(nextEvent.opponent);
        } else if (nextEvent.type === 'state_snapshot') {
          // Authoritative periodic snapshot from server. Merge into local state
          const snapTs = typeof nextEvent.timestamp === 'number' ? nextEvent.timestamp : null
          const snapSeq = (nextEvent as any).seq ?? null
          console.log(`[STATE_UPDATE] Received state snapshot at seq ${snapSeq}, timestamp ${snapTs}`)

          if (nextEvent.player_units) {
            const players = nextEvent.player_units as any[]
            const normalizedPlayers = players.map((u, idx) => ({ ...u, hp: u.hp ?? 0, current_mana: u.current_mana ?? 0, shield: u.shield ?? 0 }))
            setPlayerUnits(prev => {
              // Log desync in stats, effects, etc.
              normalizedPlayers.forEach(u => {
                const prevU = prev.find(p => p.id === u.id)
                if (prevU) {
                  if (prevU.hp !== u.hp) {
                    console.log(`[DESYNC] Player unit ${u.id} (${u.name}) HP: UI=${prevU.hp}, Server=${u.hp}`)
                  }
                  if (prevU.shield !== u.shield) {
                    console.log(`[DESYNC] Player unit ${u.id} (${u.name}) Shield: UI=${prevU.shield}, Server=${u.shield}`)
                  }
                  if (prevU.current_mana !== u.current_mana) {
                    console.log(`[DESYNC] Player unit ${u.id} (${u.name}) Mana: UI=${prevU.current_mana}, Server=${u.current_mana}`)
                  }
                  const prevEffects = prevU.effects || []
                  const serverEffects = u.effects || []
                  if (JSON.stringify(prevEffects.sort()) !== JSON.stringify(serverEffects.sort())) {
                    console.log(`[DESYNC] Player unit ${u.id} (${u.name}) effects: UI=${JSON.stringify(prevEffects)}, Server=${JSON.stringify(serverEffects)}`)
                  }
                }
              })
              const prevMap = new Map(prev.map(p => [p.id, p]))
              return normalizedPlayers.map(u => {
                const prevU = prevMap.get(u.id)
                // Preserve client-side persistent buffs when merging
                const mergedPersistent = { ...(u.persistent_buffs || {}), ...(prevU?.persistent_buffs || {}) }
                // Prefer keeping client-side active effects to avoid losing UI badges/animations
                const mergedEffects = u.effects || []
                return { ...u, persistent_buffs: mergedPersistent, effects: mergedEffects, avatar: prevU?.avatar || u.avatar, factions: prevU?.factions || u.factions, classes: prevU?.classes || u.classes, skill: prevU?.skill || u.skill }
              })
            })
          }
          if (nextEvent.opponent_units) {
            const opponents = nextEvent.opponent_units as any[]
            const normalizedOpps = opponents.map((u, idx) => ({ ...u, hp: u.hp ?? 0, current_mana: u.current_mana ?? 0, shield: u.shield ?? 0 }))
            setOpponentUnits(prev => {
              // Log desync
              normalizedOpps.forEach(u => {
                const prevU = prev.find(p => p.id === u.id)
                if (prevU) {
                  if (prevU.hp !== u.hp) {
                    console.log(`[DESYNC] Opponent unit ${u.id} (${u.name}) HP: UI=${prevU.hp}, Server=${u.hp}`)
                  }
                  if (prevU.shield !== u.shield) {
                    console.log(`[DESYNC] Opponent unit ${u.id} (${u.name}) Shield: UI=${prevU.shield}, Server=${u.shield}`)
                  }
                  if (prevU.current_mana !== u.current_mana) {
                    console.log(`[DESYNC] Opponent unit ${u.id} (${u.name}) Mana: UI=${prevU.current_mana}, Server=${u.current_mana}`)
                  }
                  const prevEffects = prevU.effects || []
                  const serverEffects = u.effects || []
                  if (JSON.stringify(prevEffects.sort()) !== JSON.stringify(serverEffects.sort())) {
                    console.log(`[DESYNC] Opponent unit ${u.id} (${u.name}) effects: UI=${JSON.stringify(prevEffects)}, Server=${JSON.stringify(serverEffects)}`)
                  }
                }
              })
              const prevMap = new Map(prev.map(p => [p.id, p]))
              return normalizedOpps.map(u => {
                const prevU = prevMap.get(u.id)
                const mergedPersistent = { ...(u.persistent_buffs || {}), ...(prevU?.persistent_buffs || {}) }
                const mergedEffects = u.effects || []
                return { ...u, persistent_buffs: mergedPersistent, effects: mergedEffects, avatar: prevU?.avatar || u.avatar, factions: prevU?.factions || u.factions, classes: prevU?.classes || u.classes, skill: prevU?.skill || u.skill }
              })
            })
          }
          if (nextEvent.synergies) setSynergies(nextEvent.synergies)
          if (nextEvent.traits) setTraits(nextEvent.traits)
          if (nextEvent.opponent) setOpponentInfo(nextEvent.opponent)

          // Drop queued events that are older than snapshot (by seq if present, else by timestamp)
          if (snapSeq !== null) {
            setEventQueue(prev => prev.filter(e => {
              const es = (e as any).seq
              if (typeof es === 'number') return es > snapSeq
              if (typeof e.timestamp === 'number' && snapTs !== null) return e.timestamp > snapTs
              return true
            }))
          } else if (snapTs !== null) {
            setEventQueue(prev => prev.filter(e => (typeof e.timestamp === 'number' ? e.timestamp > snapTs : true)))
          }

          if (snapTs !== null) lastTimestampRef.current = snapTs
        } else if (nextEvent.type === 'attack') {
          // Update HP and shield immediately on attack
          const targetId = nextEvent.target_id
          const targetHp = nextEvent.target_hp
          const shieldAbsorbed = nextEvent.shield_absorbed || 0
          const side = nextEvent.side
          if (targetId && typeof targetHp === 'number' && side) {
            if (side === 'team_a') {
              setPlayerUnits(prev => prev.map(u => 
                u.id === targetId ? { ...u, hp: targetHp, shield: Math.max(0, (u.shield || 0) - shieldAbsorbed) } : u
              ))
            } else {
              setOpponentUnits(prev => prev.map(u => 
                u.id === targetId ? { ...u, hp: targetHp, shield: Math.max(0, (u.shield || 0) - shieldAbsorbed) } : u
              ))
            }
          }
        } else if (nextEvent.type === 'unit_attack') {
          if (nextEvent.attacker_id && nextEvent.target_id) {
            const attacker = nextEvent.attacker_id as string
            const target = nextEvent.target_id as string
            // add attacker/target to active lists so animations can overlap
            setAttackingUnits(prev => [...prev, attacker])
            setTargetUnits(prev => [...prev, target])
            setAnimatingUnits(prev => [...prev, attacker, target])
            // compute animation duration based on attacker's attack_speed (attacks per second)
            const allUnits = [...playerUnits, ...opponentUnits]
            const attackerUnit = allUnits.find(u => u.id === attacker)
            const attackerAS = (attackerUnit && attackerUnit.buffed_stats?.attack_speed) || 1
            // avoid division by zero and clamp reasonable values
            const normalizedAS = Math.max(0.1, parseFloat(String(attackerAS)))
            // base interval between attacks in ms = 1000 / attack_speed
            const baseInterval = 1000 / normalizedAS
            const duration = Math.round(Math.max(150, Math.min(3000, baseInterval * animationScale / combatSpeed)))

            // set per-unit durations for UI components to use for CSS animation timings
            setAttackDurations(prev => ({ ...prev, [attacker]: duration, [target]: duration }))

            setTimeout(() => { setAttackingUnits(prev => prev.filter(id => id !== attacker)); setAttackDurations(prev => { const copy = { ...prev }; delete copy[attacker]; return copy }) }, duration)
            setTimeout(() => { setTargetUnits(prev => prev.filter(id => id !== target)); setAttackDurations(prev => { const copy = { ...prev }; delete copy[target]; return copy }) }, duration)
            setTimeout(() => { setAnimatingUnits(prev => prev.filter(id => id !== attacker && id !== target)) }, duration)
          }
          // Accept both unit_hp (preferred) and target_hp (legacy/backend)
            // Accept both unit_hp (preferred) and target_hp (legacy/backend)
            const attackHp = nextEvent.unit_hp !== undefined ? nextEvent.unit_hp : nextEvent.target_hp;
            if (nextEvent.target_id && attackHp !== undefined) {
              if (nextEvent.target_id.startsWith('opp_')) {
                setOpponentUnits(prev => prev.map(u => {
                  if (u.id !== nextEvent.target_id) return u
                  const newShield = Math.max(0, (u.shield || 0) - (nextEvent.shield_absorbed || 0))
                  return { ...u, hp: attackHp, shield: Math.round(newShield) }
                }))
              } else {
                setPlayerUnits(prev => prev.map(u => {
                  if (u.id !== nextEvent.target_id) return u
                  const newShield = Math.max(0, (u.shield || 0) - (nextEvent.shield_absorbed || 0))
                  return { ...u, hp: attackHp, shield: Math.round(newShield) }
                }))
              }
            }
          const msg = nextEvent.is_skill 
            ? `🔥 ${nextEvent.attacker_name} zadaje ${nextEvent.damage?.toFixed(2)} obrażeń ${nextEvent.target_name} (umiejętność)`
            : `⚔️ ${nextEvent.attacker_name} atakuje ${nextEvent.target_name} (${(nextEvent.damage ?? 0).toFixed(2)} dmg)`
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
          //console.log('Received stat_buff event:', nextEvent);
          const statName = nextEvent.stat === 'attack' ? 'Ataku' : nextEvent.stat === 'defense' ? 'Obrony' : nextEvent.stat || 'Statystyki';
          const buffType = nextEvent.buff_type === 'debuff' ? '⬇️' : '⬆️';
          let reason = '';
          if (nextEvent.buff_type === 'debuff') {
            reason = '(umiejętność)';
          } else if (nextEvent.cause === 'kill') {
            reason = '(zabity wróg)';
          }
          const msg = `${buffType} ${nextEvent.unit_name} ${nextEvent.buff_type === 'debuff' ? 'traci' : 'zyskuje'} ${nextEvent.amount} ${statName} ${reason}`
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
        } else if (nextEvent.type === 'heal') {
          // Update HP immediately on heal
          const unitId = nextEvent.unit_id
          const amount = nextEvent.amount
          const side = nextEvent.side
          if (unitId && typeof amount === 'number' && side) {
            const updateFn = (prev: Unit[]) => prev.map(u => 
              u.id === unitId ? { ...u, hp: Math.min(u.max_hp, u.hp + amount) } : u
            )
            if (side === 'team_a') {
              setPlayerUnits(updateFn)
            } else {
              setOpponentUnits(updateFn)
            }
          }
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
        } else if (nextEvent.type === 'damage_over_time_tick') {
          // Update unit HP and log DoT tick
          const tickHp = nextEvent.unit_hp !== undefined ? nextEvent.unit_hp : undefined
          if (nextEvent.unit_id && tickHp !== undefined) {
            if (nextEvent.unit_id.startsWith('opp_')) {
              setOpponentUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? { ...u, hp: tickHp } : u));
            } else {
              setPlayerUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? { ...u, hp: tickHp } : u));
            }
          }
          const dmg = nextEvent.damage ?? 0
          const msg = `🔥 ${nextEvent.unit_name} otrzymuje ${dmg} obrażeń (DoT)`
          setCombatLog(prev => [...prev, msg]);
          // small visual flash on target
          if (nextEvent.unit_id) {
            const unitId = nextEvent.unit_id as string
            setTargetUnits(prev => [...prev, unitId])
            const dur = Math.round(600 * animationScale / combatSpeed)
            setTimeout(() => setTargetUnits(prev => prev.filter(id => id !== unitId)), dur)
          }
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
          console.log('Processing skill_cast event:', nextEvent);
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
        } else if (nextEvent.type === 'shield_applied') {
          // Update shield immediately
          const unitId = nextEvent.unit_id
          const amount = nextEvent.amount
          if (unitId && typeof amount === 'number') {
            const updateFn = (prev: Unit[]) => prev.map(u => 
              u.id === unitId ? { ...u, shield: (u.shield || 0) + amount } : u
            )
            if (unitId.startsWith('opp_')) {
              setOpponentUnits(updateFn)
            } else {
              setPlayerUnits(updateFn)
            }
          }
          const msg = `🛡️ ${nextEvent.unit_name} zyskuje ${nextEvent.amount} tarczy na ${nextEvent.duration}s`
          setCombatLog(prev => [...prev, msg]);
          if (nextEvent.unit_id) {
            const effect: EffectSummary = {
              type: 'shield',
              amount: nextEvent.amount,
              duration: nextEvent.duration,
              caster_name: nextEvent.caster_name,
              expiresAt: nextEvent.duration ? Date.now() + (nextEvent.duration * 1000) : undefined
            }
            if (nextEvent.unit_id.startsWith('opp_')) {
              setOpponentUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? { ...u, effects: [...(u.effects || []), effect], shield: Math.max(0, (u.shield || 0) + (nextEvent.amount || 0)) } : u));
            } else {
              setPlayerUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? { ...u, effects: [...(u.effects || []), effect], shield: Math.max(0, (u.shield || 0) + (nextEvent.amount || 0)) } : u));
            }
          }
        } else if (nextEvent.type === 'unit_stunned') {
          const msg = `😵 ${nextEvent.unit_name} jest ogłuszony na ${nextEvent.duration}s`
          setCombatLog(prev => [...prev, msg]);
          if (nextEvent.unit_id) {
            const effect: EffectSummary = {
              type: 'stun',
              duration: nextEvent.duration,
              caster_name: nextEvent.caster_name,
              expiresAt: nextEvent.duration ? Date.now() + (nextEvent.duration * 1000) : undefined
            }
            if (nextEvent.unit_id.startsWith('opp_')) {
              setOpponentUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? { ...u, effects: [...(u.effects || []), effect] } : u));
            } else {
              setPlayerUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? { ...u, effects: [...(u.effects || []), effect] } : u));
            }
          }
        }

        else if (nextEvent.type === 'damage_over_time_applied') {
          // DoT applied: attach effect summary so UI shows burn/DoT badge
          const msg = `🔥 ${nextEvent.unit_name} otrzymuje DoT (${nextEvent.ticks || '?'} ticks)`
          setCombatLog(prev => [...prev, msg]);
          if (nextEvent.unit_id) {
            const effect: EffectSummary = {
              type: 'damage_over_time',
              damage: nextEvent.damage || nextEvent.amount,
              duration: nextEvent.duration,
              ticks: nextEvent.ticks,
              interval: nextEvent.interval,
              caster_name: nextEvent.caster_name,
              expiresAt: nextEvent.duration ? Date.now() + (nextEvent.duration * 1000) : undefined
            }
            if (nextEvent.unit_id.startsWith('opp_')) {
              setOpponentUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? { ...u, effects: [...(u.effects || []), effect] } : u));
            } else {
              setPlayerUnits(prev => prev.map(u => u.id === nextEvent.unit_id ? { ...u, effects: [...(u.effects || []), effect] } : u));
            }
          }
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
      
      // Cleanup expired effects on units
      setPlayerUnits(prev => {
        let changed = false
        const next = prev.map(u => {
          if (!u.effects || u.effects.length === 0) return u
          const remaining = u.effects.filter((e: EffectSummary) => !e.expiresAt || e.expiresAt > now)
          if (remaining.length !== u.effects.length) {
            changed = true
            // Compute removed effects to adjust numeric shields if needed
            const removed = u.effects.filter((e: EffectSummary) => !(remaining.includes(e)))
            let newShield = u.shield || 0
            for (const r of removed) {
              if (r.type === 'shield' && r.amount) {
                newShield = Math.max(0, newShield - r.amount)
              }
            }
            return { ...u, effects: remaining, shield: Math.round(newShield) }
          }
          return u
        })
        return changed ? next : prev
      })

      setOpponentUnits(prev => {
        let changed = false
        const next = prev.map(u => {
          if (!u.effects || u.effects.length === 0) return u
          const remaining = u.effects.filter((e: EffectSummary) => !e.expiresAt || e.expiresAt > now)
          if (remaining.length !== u.effects.length) {
            changed = true
            const removed = u.effects.filter((e: EffectSummary) => !(remaining.includes(e)))
            let newShield = u.shield || 0
            for (const r of removed) {
              if (r.type === 'shield' && r.amount) {
                newShield = Math.max(0, newShield - r.amount)
              }
            }
            return { ...u, effects: remaining, shield: Math.round(newShield) }
          }
          return u
        })
        return changed ? next : prev
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
    attackDurations,
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
