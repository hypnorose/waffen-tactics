import { getUnit, getCostColor, getCostBorderColor, getFactionColor } from '../data/units'

interface UnitCardProps {
  unitId: string
  starLevel?: number
  onClick?: () => void
  disabled?: boolean
  showCost?: boolean
}

export default function UnitCard({ unitId, starLevel = 1, onClick, disabled, showCost = true }: UnitCardProps) {
  const unit = getUnit(unitId)
  
  if (!unit) {
    return (
      <div className="p-2 bg-red-900/20 border-2 border-red-500 rounded-lg w-32">
        <p className="text-red-500 text-xs">Unknown: {unitId}</p>
      </div>
    )
  }

  // Calculate stats based on star level (2★ = 2x, 3★ = 3x)
  const multiplier = starLevel
  const scaledStats = unit.stats ? {
    hp: Math.floor(unit.stats.hp * multiplier),
    attack: Math.floor(unit.stats.attack * multiplier),
    defense: Math.floor(unit.stats.defense * multiplier),
    attack_speed: unit.stats.attack_speed
  } : null

  return (
    <div 
      onClick={!disabled ? onClick : undefined}
      className={`relative group w-48 ${
        onClick && !disabled ? 'cursor-pointer' : ''
      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      {/* Detailed Stats Tooltip - Positioned to right side to avoid top/bottom overflow */}
      <div 
        className="hidden group-hover:block absolute p-3 rounded-lg z-[100] shadow-2xl text-xs w-[280px] border-2 pointer-events-none"
        style={{
          backgroundColor: '#0f172a',
          borderColor: getCostBorderColor(unit.cost),
          left: 'calc(100% + 0.5rem)',
          top: '0',
          maxHeight: '90vh',
          overflowY: 'auto'
        }}
      >
        <div className="mb-2">
          <div className="font-bold text-sm text-white mb-1">{unit.name}</div>
          <div className="text-gray-400 text-xs mb-2">
            {starLevel > 1 && <span className="text-yellow-400">{'⭐'.repeat(starLevel)} </span>}
            Tier {unit.cost}
          </div>
          <div className="flex flex-wrap gap-1 mb-2">
            {unit.factions.slice(0, 2).map(faction => (
              <span key={faction} className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${getFactionColor(faction)} text-white`}>
                {faction}
              </span>
            ))}
            {unit.classes.slice(0, 2).map(cls => (
              <span key={cls} className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-purple-600/60 text-white">
                {cls}
              </span>
            ))}
          </div>
        </div>

        {/* Detailed Stats */}
        {scaledStats && (
          <div className="space-y-2">
            <div className="flex items-center justify-between py-1">
              <span className="text-red-400 flex items-center gap-1">
                <span className="text-base">❤️</span>
                <span className="font-semibold">Życie</span>
              </span>
              <span className="font-bold text-white text-sm">{scaledStats.hp}</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-orange-400 flex items-center gap-1">
                <span className="text-base">⚔️</span>
                <span className="font-semibold">Atak</span>
              </span>
              <span className="font-bold text-white text-sm">{scaledStats.attack}</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-blue-400 flex items-center gap-1">
                <span className="text-base">🛡️</span>
                <span className="font-semibold">Obrona</span>
              </span>
              <span className="font-bold text-white text-sm">{scaledStats.defense}</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-green-400 flex items-center gap-1">
                <span className="text-base">⚡</span>
                <span className="font-semibold">Prędkość ataku</span>
              </span>
              <span className="font-bold text-white text-sm">{scaledStats.attack_speed.toFixed(2)}</span>
            </div>
            <div className="flex items-center justify-between py-1 border-t border-gray-700 pt-2">
              <span className="text-purple-400 flex items-center gap-1">
                <span className="text-base">🔮</span>
                <span className="font-semibold">Max Mana</span>
              </span>
              <span className="font-bold text-white text-sm">100</span>
            </div>
          </div>
        )}

        {starLevel > 1 && (
          <div className="mt-3 pt-2 border-t border-gray-700 text-xs text-gray-400">
            <div className="flex items-center gap-1">
              <span className="text-yellow-400">✨</span>
              Statystyki x{starLevel} (gwiazdka {starLevel})
            </div>
          </div>
        )}
      </div>
      {/* Card with rarity border */}
      <div 
        className="rounded-lg p-2 transition-all border-2 bg-gray-800/90 hover:bg-gray-800 h-48 flex flex-col"
        style={{
          borderColor: getCostBorderColor(unit.cost),
          boxShadow: `0 0 10px ${getCostBorderColor(unit.cost)}40`
        }}
      >
        {/* Star Level Badge - Right side center edge */}
        {starLevel > 1 && (
          <div className="absolute top-1/2 -right-2 -translate-y-1/2 bg-yellow-500 px-1.5 py-1 rounded-full text-[10px] font-bold z-10 border border-yellow-600 shadow-lg">
            {'⭐'.repeat(starLevel)}
          </div>
        )}

        {/* Avatar Placeholder */}
        <div className="flex justify-center mb-2">
          <div 
            className="w-16 h-16 rounded-full flex items-center justify-center font-bold text-2xl border-2 relative overflow-hidden"
            style={{
              borderColor: getCostBorderColor(unit.cost),
              backgroundColor: '#1e293b'
            }}
          >
            {/* Unit image or placeholder */}
            {unit.avatar ? (
              <img 
                src={unit.avatar} 
                alt={unit.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  // Fallback to emoji if image fails to load
                  e.currentTarget.style.display = 'none'
                  const placeholder = document.createElement('span')
                  placeholder.className = 'text-3xl'
                  placeholder.textContent = '👤'
                  e.currentTarget.parentElement!.appendChild(placeholder)
                }}
              />
            ) : (
              <span className="text-3xl">👤</span>
            )}
            {/* Cost badge overlay */}
            {showCost && (
              <div 
                className="absolute bottom-0 right-0 w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold border"
                style={{
                  backgroundColor: getCostBorderColor(unit.cost),
                  borderColor: '#1e293b',
                  color: '#000'
                }}
              >
                {unit.cost}
              </div>
            )}
          </div>
        </div>

        {/* Unit Name */}
        <h3 className="text-center text-xs font-bold mb-1 truncate px-1">{unit.name}</h3>
        
        {/* Traits - compact */}
        <div className="flex flex-wrap gap-0.5 justify-center mb-2 px-1">
          {unit.factions.slice(0, 1).map(faction => (
            <span key={faction} className={`px-1 py-0.5 rounded text-[9px] ${getFactionColor(faction)} text-white`}>
              {faction}
            </span>
          ))}
          {unit.classes.slice(0, 1).map(cls => (
            <span key={cls} className="px-1 py-0.5 rounded text-[9px] bg-purple-600/60 text-white">
              {cls}
            </span>
          ))}
        </div>

        {/* Stats - compact */}
        {scaledStats && (
          <div className="text-[10px] space-y-0.5 flex-1 flex flex-col justify-end">
            <div className="flex justify-between px-1">
              <span className="text-gray-400">❤️</span>
              <span className="font-bold">{scaledStats.hp}</span>
            </div>
            <div className="flex justify-between px-1">
              <span className="text-gray-400">⚔️</span>
              <span className="font-bold">{scaledStats.attack}</span>
            </div>
            <div className="flex justify-between px-1">
              <span className="text-gray-400">🛡️</span>
              <span className="font-bold">{scaledStats.defense}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
