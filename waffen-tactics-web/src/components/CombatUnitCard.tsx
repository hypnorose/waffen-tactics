import { useState } from 'react'

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
  avatar?: string
  buffed_stats?: {
    hp?: number
    attack?: number
    defense?: number
    attack_speed?: number
    max_mana?: number
    hp_regen_per_sec?: number
  }
  current_mana?: number
}

interface Props {
  unit: Unit
  isOpponent?: boolean
  attackingUnits?: string[]
  targetUnits?: string[]
  regen?: { amount_per_sec: number } | undefined
}

const getRarityColor = (cost?: number) => {
  if (!cost) return '#6b7280'
  if (cost === 1) return '#6b7280'
  if (cost === 2) return '#10b981'
  if (cost === 3) return '#3b82f6'
  if (cost === 4) return '#a855f7'
  if (cost === 5) return '#f59e0b'
  return '#6b7280'
}

export default function CombatUnitCard({ unit, isOpponent, attackingUnits = [], targetUnits = [], regen }: Props) {
  const [showTooltip, setShowTooltip] = useState(false)
  const displayMaxHp = unit.buffed_stats?.hp ?? unit.max_hp
  const displayHp = Math.min(unit.hp, displayMaxHp)
  const displayAttack = unit.buffed_stats?.attack ?? unit.attack
  const displayDefense = unit.buffed_stats?.defense ?? unit.defense ?? 0
  const displayAS = unit.buffed_stats?.attack_speed ?? 0
  const displayMaxMana = unit.buffed_stats?.max_mana ?? 100
  const displayMana = unit.current_mana ?? 0
  const displayHpRegen = unit.buffed_stats?.hp_regen_per_sec ?? 0

  return (
    <div
      className="group"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      style={{
        backgroundColor: '#0f172a',
        borderRadius: isOpponent ? '0.25rem' : '0.5rem',
        padding: isOpponent ? '0.25rem' : '0.5rem',
        border: `2px solid ${unit.hp > 0 ? getRarityColor(unit.cost) : '#374151'}`,
        opacity: unit.hp > 0 ? 1 : 0.4,
        transition: 'all 0.3s',
        boxShadow:
          attackingUnits.includes(unit.id)
            ? '0 0 20px #ff0000, 0 0 30px #ff0000'
            : targetUnits.includes(unit.id)
            ? '0 0 20px #ffff00, 0 0 30px #ffff00'
            : unit.hp > 0
            ? `0 0 10px ${getRarityColor(unit.cost)}40`
            : 'none',
        transform: attackingUnits.includes(unit.id) ? 'scale(1.1)' : 'scale(1)',
        minWidth: 0,
        position: 'relative',
        width: '120px',
        flexShrink: 0,
      }}
    >
      {attackingUnits.includes(unit.id) && (
        <div style={{ position: 'absolute', top: '-10px', right: '-10px', fontSize: '1.5rem', animation: 'pulse 0.6s ease-in-out' }}>
          ⚔️
        </div>
      )}
      {targetUnits.includes(unit.id) && (
        <div style={{ position: 'absolute', top: '-10px', right: '-10px', fontSize: '1.5rem', animation: 'pulse 0.6s ease-in-out' }}>
          💥
        </div>
      )}

      {unit.avatar && (
        <img src={unit.avatar} alt={unit.name} style={{ width: '100%', height: '60px', objectFit: 'cover', borderRadius: '0.25rem', marginBottom: '0.25rem' }} />
      )}

      <div className="text-xs font-bold text-white mb-1 text-center truncate">
        {unit.name} ⭐{unit.star_level}
      </div>

      {unit.factions && unit.factions.length > 0 && !isOpponent && (
        <div className="flex flex-wrap gap-1 justify-center mb-1">
          {unit.factions.slice(0, 2).map((f) => (
            <span key={f} className="text-[9px] px-1 py-0.5 bg-blue-500/30 rounded text-blue-200">
              {f}
            </span>
          ))}
        </div>
      )}

      <div className="relative h-2 bg-gray-700 rounded-full overflow-hidden border border-gray-600">
        <div
          className="absolute inset-y-0 left-0 transition-all duration-300"
          style={{
            width: `${displayMaxHp > 0 ? (displayHp / displayMaxHp) * 100 : 0}%`,
            background: `linear-gradient(to right, ${getRarityColor(unit.cost)}, ${getRarityColor(unit.cost)}dd)`,
          }}
        />
      </div>

      <div className="relative h-2 bg-gray-700 rounded-full overflow-hidden border border-gray-600 mt-1">
        <div
          className="absolute inset-y-0 left-0 transition-all duration-300"
          style={{
            width: `${displayMaxMana > 0 ? (displayMana / displayMaxMana) * 100 : 0}%`,
            background: 'linear-gradient(to right, #8b5cf6, #a855f7)',
          }}
        />
      </div>

      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 bg-gray-800 border border-gray-600 text-white text-sm rounded-lg p-4 shadow-xl z-[100] min-w-[300px]">
          <div className="flex items-center mb-3">
            {unit.avatar && (
              <img src={unit.avatar} alt={unit.name} className="w-10 h-10 rounded mr-3 object-cover" />
            )}
            <div>
              <div className="font-bold text-base">{unit.name}</div>
              <div className="text-yellow-400">⭐ {unit.star_level} • Koszt: {unit.cost}</div>
            </div>
          </div>
          {(unit.factions && unit.factions.length > 0) && (
            <div className="flex flex-wrap gap-1 mb-2">
              {unit.factions.map((f) => (
                <span key={f} className="bg-blue-500/30 px-2 py-1 rounded text-sm">{f}</span>
              ))}
            </div>
          )}
          {(unit.classes && unit.classes.length > 0) && (
            <div className="flex flex-wrap gap-1 mb-2">
              {unit.classes.map((c) => (
                <span key={c} className="bg-green-500/30 px-2 py-1 rounded text-sm">{c}</span>
              ))}
            </div>
          )}
          {unit.position && (
            <div className="mb-2">
              <span className="bg-purple-500/30 px-2 py-1 rounded text-sm">{unit.position === 'front' ? 'Front' : 'Tył'}</span>
            </div>
          )}
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div>❤️ HP: {Math.floor(displayHp)}/{Math.floor(displayMaxHp)}</div>
            <div>⚔️ ATK: {displayAttack}</div>
            <div>🛡️ DEF: {displayDefense}</div>
            <div>⚡ SPD: {displayAS.toFixed(2)}</div>
            <div>🔮 Mana: {Math.floor(displayMana)}/{Math.floor(displayMaxMana)}</div>
            {displayHpRegen > 0 && <div>💚 Regen: +{Math.round(displayHpRegen)}/s</div>}
          </div>
          {/* Arrow */}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800"></div>
        </div>
      )}

      {displayHpRegen > 0 && unit.hp > 0 && (
        <div
          style={{
            position: 'absolute',
            top: '6px',
            left: '6px',
            background: 'linear-gradient(90deg,#10b981,#34d399)',
            color: '#03241a',
            padding: '2px 6px',
            borderRadius: '999px',
            fontSize: '10px',
            fontWeight: '700',
            boxShadow: '0 4px 10px rgba(16,185,129,0.15)',
          }}
        >
          +{Math.round(displayHpRegen)}/s
        </div>
      )}
    </div>
  )
}
