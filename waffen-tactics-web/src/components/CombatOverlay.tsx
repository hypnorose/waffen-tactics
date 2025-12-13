import { useState, useEffect, useRef } from 'react'
import { PlayerState } from '../store/gameStore'
import { useAuthStore } from '../store/authStore'
import GoldNotification from './GoldNotification'

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
  target_hp?: number
  target_max_hp?: number
  unit_id?: string
  round?: number
  state?: PlayerState
}

interface Props {
  onClose: (newState?: PlayerState) => void
}

const getRarityColor = (cost?: number) => {
  if (!cost) return '#6b7280'
  if (cost === 1) return '#6b7280' // gray
  if (cost === 2) return '#10b981' // green
  if (cost === 3) return '#3b82f6' // blue
  if (cost === 4) return '#a855f7' // purple
  if (cost === 5) return '#f59e0b' // orange/gold
  return '#6b7280'
}

const getRarityGlow = (cost?: number) => {
  const color = getRarityColor(cost)
  return `0 0 10px ${color}40`
}

const getTraitColor = (tier: number) => {
  if (tier === 0) return '#6b7280' // gray - inactive
  const tierColors = ['#6b7280', '#10b981', '#3b82f6', '#a855f7', '#f59e0b']
  if (tier >= tierColors.length - 1) return tierColors[tierColors.length - 1]
  return tierColors[tier] || '#6b7280'
}

export default function CombatOverlay({ onClose }: Props) {
  const { token } = useAuthStore()
  const [playerUnits, setPlayerUnits] = useState<Unit[]>([])
  const [opponentUnits, setOpponentUnits] = useState<Unit[]>([])
  const [combatLog, setCombatLog] = useState<string[]>([])
  const [isFinished, setIsFinished] = useState(false)
  const [finalState, setFinalState] = useState<PlayerState | null>(null)
  const [synergies, setSynergies] = useState<Record<string, {count: number, tier: number}>>({})
  const [hoveredTrait, setHoveredTrait] = useState<string | null>(null)
  const [opponentInfo, setOpponentInfo] = useState<{name: string, wins: number, level: number} | null>(null)
  const [showLog, setShowLog] = useState(true)
  const [attackingUnit, setAttackingUnit] = useState<string | null>(null)
  const [targetUnit, setTargetUnit] = useState<string | null>(null)
  const [combatSpeed, setCombatSpeed] = useState(() => {
    const saved = localStorage.getItem('combatSpeed')
    return saved ? parseFloat(saved) : 1
  })
  const [eventQueue, setEventQueue] = useState<CombatEvent[]>([])
  const [isPlaying, setIsPlaying] = useState(false)
  const [storedGoldBreakdown, setStoredGoldBreakdown] = useState<{base: number, interest: number, milestone: number, win_bonus: number, total: number} | null>(null)
  const [displayedGoldBreakdown, setDisplayedGoldBreakdown] = useState<{base: number, interest: number, milestone: number, win_bonus: number, total: number} | null>(null)
  const logEndRef = useRef<HTMLDivElement>(null)

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
    if (!isPlaying || eventQueue.length === 0) return
    const processNextEvent = () => {
      setEventQueue(prev => {
        if (prev.length === 0) return prev
        const [nextEvent, ...rest] = prev
        if (nextEvent.type === 'units_init') {
          if (nextEvent.player_units) setPlayerUnits(nextEvent.player_units)
          if (nextEvent.opponent_units) setOpponentUnits(nextEvent.opponent_units)
          if (nextEvent.synergies) setSynergies(nextEvent.synergies)
          if (nextEvent.opponent) setOpponentInfo(nextEvent.opponent)
        } else if (nextEvent.type === 'unit_attack') {
          if (nextEvent.attacker_id && nextEvent.target_id) {
            setAttackingUnit(nextEvent.attacker_id)
            setTargetUnit(nextEvent.target_id)
            setTimeout(() => { setAttackingUnit(null); setTargetUnit(null) }, 1500 / combatSpeed)
          }
          if (nextEvent.target_id && nextEvent.target_hp !== undefined) {
            if (nextEvent.target_id.startsWith('opp_')) setOpponentUnits(prev => prev.map(u => u.id === nextEvent.target_id ? { ...u, hp: nextEvent.target_hp! } : u))
            else setPlayerUnits(prev => prev.map(u => u.id === nextEvent.target_id ? { ...u, hp: nextEvent.target_hp! } : u))
          }
        } else if (nextEvent.type === 'gold_income') {
          const breakdown = nextEvent as any
          setStoredGoldBreakdown({ base: breakdown.base || 0, interest: breakdown.interest || 0, milestone: breakdown.milestone || 0, win_bonus: breakdown.win_bonus || 0, total: breakdown.total || 0 })
        } else if (nextEvent.type === 'end') {
          setIsFinished(true)
          if (nextEvent.state) setFinalState(nextEvent.state)
          setIsPlaying(false)
        }
        if (nextEvent.message) setCombatLog(prev => [...prev, nextEvent.message!])
        return rest
      })
    }
    const getEventDelay = (event: CombatEvent) => {
      if (event.type === 'units_init') return 500
      if (event.type === 'round') return 1500 / combatSpeed
      if (event.type === 'unit_attack') return 800 / combatSpeed
      if (event.type === 'unit_died') return 500 / combatSpeed
      if (event.type === 'end') return 1000 / combatSpeed
      return 300 / combatSpeed
    }
    const timer = setTimeout(processNextEvent, getEventDelay(eventQueue[0]))
    return () => clearTimeout(timer)
  }, [eventQueue, isPlaying, combatSpeed])

  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [combatLog])
  const handleClose = () => onClose(finalState || undefined)
  const handleGoldDismiss = () => { setDisplayedGoldBreakdown(null); setStoredGoldBreakdown(null); handleClose() }

  return (
    <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.95)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
      <div style={{ backgroundColor: '#1e293b', borderRadius: '0.75rem', width: '1400px', height: '850px', display: 'flex', flexDirection: 'column', border: '3px solid #475569', boxShadow: '0 20px 60px rgba(0,0,0,0.5)' }}>
        {/* Header */}
        <div className="bg-gradient-to-r from-red-900 to-red-700 p-3">
          <div className="flex items-center justify-between">
            <div className="flex-1" />
            <div className="flex-1">
              <h2 className="text-xl font-bold text-center text-white">⚔️ WALKA ⚔️</h2>
              {opponentInfo && (<div className="text-center text-sm text-red-100 mt-1">vs {opponentInfo.name} (Lvl {opponentInfo.level}, {opponentInfo.wins} W)</div>)}
            </div>
            <input type="range" min="-10" max="10" step="1" value={Math.log10(combatSpeed) * 10} onChange={(e) => { const sliderValue = parseFloat(e.target.value); const newSpeed = Math.pow(10, sliderValue / 10); setCombatSpeed(newSpeed); localStorage.setItem('combatSpeed', newSpeed.toString()) }} className="w-32 h-2 bg-red-800 rounded-lg appearance-none cursor-pointer" style={{ accentColor: '#fbbf24' }} />
            <div className="text-xs text-yellow-400 font-bold min-w-[42px]">{combatSpeed.toFixed(1)}x</div>
          </div>
        </div>

        {/* Combat Area */}
        <div style={{ flex: 1, padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', overflow: 'hidden' }}>

          {/* Combat Stats & Traits */}
          <div className="bg-gray-800 rounded-lg p-3 border border-gray-700" style={{ flexShrink: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-around', alignItems: 'center', flex: 1 }}>
                <div className="text-center">
                  <div className="text-xs text-gray-400 mb-1">Twoje jednostki</div>
                  <div className="text-lg font-bold text-green-400">{playerUnits.filter(u => u.hp > 0).length} / {playerUnits.length}</div>
                </div>
                <div className="text-2xl">⚔️</div>
                <div className="text-center">
                  <div className="text-xs text-gray-400 mb-1">Przeciwnik</div>
                  <div className="text-lg font-bold text-red-400">{opponentUnits.filter(u => u.hp > 0).length} / {opponentUnits.length}</div>
                </div>
              </div>

              {Object.keys(synergies).length > 0 && (
                <div style={{ flex: 1 }}>
                  <div className="text-xs text-gray-400 mb-2">✨ Aktywne Synergies</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                    {Object.entries(synergies).map(([name, data]) => (
                      <div key={name} onMouseEnter={() => setHoveredTrait(name)} onMouseLeave={() => setHoveredTrait(null)} style={{ position: 'relative', padding: '0.25rem 0.5rem', borderRadius: '0.25rem', fontSize: '0.75rem', fontWeight: 'bold', backgroundColor: `${getTraitColor(data.tier)}30`, border: `1.5px solid ${getTraitColor(data.tier)}`, color: getTraitColor(data.tier), cursor: 'pointer', transition: 'all 0.2s' }}>
                        {name} [{data.count}] T{data.tier}
                        {hoveredTrait === name && (
                          <div style={{ position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)', marginBottom: '0.5rem', padding: '0.5rem', backgroundColor: '#1e293b', border: `2px solid ${getTraitColor(data.tier)}`, borderRadius: '0.375rem', whiteSpace: 'nowrap', zIndex: 100, boxShadow: '0 4px 12px rgba(0,0,0,0.5)', fontSize: '0.7rem', color: '#e2e8f0' }}>
                            <div style={{ fontWeight: 'bold', marginBottom: '0.25rem' }}>{name}</div>
                            <div>Tier {data.tier} aktywny ({data.count} jednostek)</div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Player Units */}
          <div className="bg-gray-800 rounded-lg p-3 border border-gray-700" style={{ flexShrink: 0 }}>
            <h3 className="text-sm font-bold text-green-400 mb-2 text-center">🛡️ Twoje Jednostki</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.5rem' }}>
              {playerUnits.map(unit => {
                const displayMaxHp = unit.buffed_stats?.hp ?? unit.max_hp
                const displayHp = Math.min(unit.hp, displayMaxHp)
                const displayAttack = unit.buffed_stats?.attack ?? unit.attack
                const displayDefense = unit.buffed_stats?.defense ?? unit.defense
                const displayAS = unit.buffed_stats?.attack_speed ?? 0
                const displayMaxMana = unit.buffed_stats?.max_mana ?? 100
                const displayMana = displayMaxMana // start full; combat events may later update
                return (
                  <div key={unit.id} style={{ backgroundColor: '#0f172a', borderRadius: '0.5rem', padding: '0.5rem', border: `2px solid ${unit.hp > 0 ? getRarityColor(unit.cost) : '#374151'}`, opacity: unit.hp > 0 ? 1 : 0.4, transition: 'all 0.3s', boxShadow: attackingUnit === unit.id ? '0 0 20px #ff0000, 0 0 30px #ff0000' : targetUnit === unit.id ? '0 0 20px #ffff00, 0 0 30px #ffff00' : unit.hp > 0 ? getRarityGlow(unit.cost) : 'none', transform: attackingUnit === unit.id ? 'scale(1.1)' : 'scale(1)', minWidth: 0, position: 'relative' }}>
                    {attackingUnit === unit.id && (<div style={{ position: 'absolute', top: '-10px', right: '-10px', fontSize: '1.5rem', animation: 'pulse 0.6s ease-in-out' }}>⚔️</div>)}
                    {targetUnit === unit.id && (<div style={{ position: 'absolute', top: '-10px', right: '-10px', fontSize: '1.5rem', animation: 'pulse 0.6s ease-in-out' }}>💥</div>)}
                    <div className="text-xs font-bold text-white mb-1 text-center truncate">{unit.name} ⭐{unit.star_level}</div>
                    {unit.factions && unit.factions.length > 0 && (<div className="flex flex-wrap gap-1 justify-center mb-1">{unit.factions.slice(0, 2).map(f => (<span key={f} className="text-[9px] px-1 py-0.5 bg-blue-500/30 rounded text-blue-200">{f}</span>))}</div>)}
                    <div className="space-y-0.5 text-[9px] text-gray-300 mb-1">
                      <div className="flex justify-between"><span>❤️ HP</span><span className="font-bold">{Math.floor(displayHp)}/{Math.floor(displayMaxHp)}</span></div>
                      <div className="flex justify-between"><span>⚔️ ATK</span><span className="font-bold">{displayAttack}</span></div>
                      <div className="flex justify-between"><span>🛡️ DEF</span><span className="font-bold">{displayDefense}</span></div>
                      <div className="flex justify-between"><span>⚡ SPD</span><span className="font-bold">{displayAS.toFixed(2)}</span></div>
                      <div className="flex items-center gap-2 mt-1"><span className="text-xs text-gray-400">🔮 Mana</span>
                        <div className="relative flex-1 h-2 bg-gray-700 rounded-full overflow-hidden border border-gray-600"><div className="absolute inset-y-0 left-0 transition-all duration-300" style={{ width: `${displayMana / Math.max(1, displayMaxMana) * 100}%`, background: `linear-gradient(to right, #7c3aed, #06b6d4)` }} /></div>
                        <span className="font-semibold text-[10px]">{Math.floor(displayMana)}/{Math.floor(displayMaxMana)}</span>
                      </div>
                    </div>
                    <div className="relative h-2 bg-gray-700 rounded-full overflow-hidden border border-gray-600"><div className="absolute inset-y-0 left-0 transition-all duration-300" style={{ width: `${(displayHp / Math.max(1, displayMaxHp)) * 100}%`, background: `linear-gradient(to right, ${getRarityColor(unit.cost)}, ${getRarityColor(unit.cost)}dd)` }} /></div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Opponent Units */}
          <div className="bg-gray-800 rounded-lg p-3 border border-gray-700" style={{ flexShrink: 0 }}>
            <h3 className="text-sm font-bold text-red-400 mb-2 text-center">⚔️ Przeciwnik</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.5rem' }}>
              {opponentUnits.map(unit => {
                const displayMaxHp = unit.buffed_stats?.hp ?? unit.max_hp
                const displayHp = Math.min(unit.hp, displayMaxHp)
                const displayAttack = unit.buffed_stats?.attack ?? unit.attack
                return (
                  <div key={unit.id} style={{ backgroundColor: '#0f172a', borderRadius: '0.25rem', padding: '0.25rem', border: `2px solid ${unit.hp > 0 ? getRarityColor(unit.cost) : '#374151'}`, opacity: unit.hp > 0 ? 1 : 0.4, transition: 'all 0.3s', boxShadow: attackingUnit === unit.id ? '0 0 20px #ff0000, 0 0 30px #ff0000' : targetUnit === unit.id ? '0 0 20px #ffff00, 0 0 30px #ffff00' : unit.hp > 0 ? getRarityGlow(unit.cost) : 'none', transform: attackingUnit === unit.id ? 'scale(1.1)' : 'scale(1)', minWidth: 0, maxWidth: '100%', display: 'flex', flexDirection: 'column', gap: '0.125rem', position: 'relative' }}>
                    {attackingUnit === unit.id && (<div style={{ position: 'absolute', top: '-10px', right: '-10px', fontSize: '1.5rem', animation: 'pulse 0.6s ease-in-out' }}>⚔️</div>)}
                    {targetUnit === unit.id && (<div style={{ position: 'absolute', top: '-10px', right: '-10px', fontSize: '1.5rem', animation: 'pulse 0.6s ease-in-out' }}>💥</div>)}
                    <div style={{ fontSize: '0.6rem', fontWeight: 'bold', color: 'white', textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{unit.name}</div>
                    <div style={{ fontSize: '0.55rem', textAlign: 'center', color: '#fbbf24' }}>{'⭐'.repeat(unit.star_level)}</div>
                    <div style={{ fontSize: '0.5rem', color: '#9ca3af', textAlign: 'center' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0 0.125rem' }}><span>❤️</span><span style={{ fontWeight: 'bold' }}>{Math.floor(displayHp)}/{Math.floor(displayMaxHp)}</span></div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0 0.125rem' }}><span>⚔️</span><span style={{ fontWeight: 'bold' }}>{displayAttack}</span></div>
                    </div>
                    <div className="relative h-2 bg-gray-700 rounded-full overflow-hidden border border-gray-600"><div className="absolute inset-y-0 left-0 transition-all duration-300" style={{ width: `${displayMaxHp > 0 ? (displayHp / displayMaxHp) * 100 : 0}%`, background: `linear-gradient(to right, ${getRarityColor(unit.cost)}, ${getRarityColor(unit.cost)}dd)` }} /></div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Combat Log */}
          <div className="bg-gray-800 rounded-lg p-2 border border-gray-700" style={{ display: 'flex', flexDirection: 'column', height: '100px', flexShrink: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <h3 className="text-xs font-bold text-gray-400">📜 Log walki</h3>
              <button onClick={() => setShowLog(!showLog)} style={{ fontSize: '0.65rem', padding: '0.125rem 0.5rem', backgroundColor: '#374151', borderRadius: '0.25rem', color: '#9ca3af', border: 'none', cursor: 'pointer' }}>{showLog ? 'Ukryj' : 'Pokaż'}</button>
            </div>
            {showLog && <div style={{ flex: 1, overflowY: 'auto' }} className="space-y-1 text-xs text-gray-300 font-mono">{combatLog.map((msg, idx) => (<div key={idx}>{msg}</div>))}<div ref={logEndRef} /></div>}
          </div>

        </div>

        {/* Footer with Continue Button */}
        <div className="bg-gray-800 p-4 border-t border-gray-700">
          {isFinished ? (
            <button onClick={() => { if (storedGoldBreakdown && !displayedGoldBreakdown) { setDisplayedGoldBreakdown(storedGoldBreakdown); return } handleClose() }} className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 text-white font-bold py-3 px-6 rounded-lg transition-all">Kontynuuj</button>
          ) : (
            <div className="text-center text-gray-400"><div className="inline-block animate-pulse">⚔️ Walka trwa...</div></div>
          )}
        </div>
      </div>

      {/* Gold Notification Overlay */}
      <GoldNotification breakdown={displayedGoldBreakdown} onDismiss={handleGoldDismiss} />
    </div>
  )
}
