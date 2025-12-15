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

      <div className="space-y-0.5 text-[9px] text-gray-300 mb-1">
        <div className="flex justify-between">
          <span>❤️ HP</span>
          <span className="font-bold">
            {Math.floor(displayHp)}/{Math.floor(displayMaxHp)}
          </span>
        </div>
        <div className="flex justify-between">
          <span>⚔️ ATK</span>
          <span className="font-bold">{displayAttack}</span>
        </div>
        <div className="flex justify-between">
          <span>🛡️ DEF</span>
          <span className="font-bold">{displayDefense}</span>
        </div>
        <div className="flex justify-between">
          <span>⚡ SPD</span>
          <span className="font-bold">{displayAS.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span>🔮 Mana</span>
          <span className="font-bold">
            {Math.floor(displayMana)}/{Math.floor(displayMaxMana)}
          </span>
        </div>
      </div>

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
