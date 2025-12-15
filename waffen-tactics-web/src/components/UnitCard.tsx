import { getUnit, getCostBorderColor, getFactionColor } from '../data/units'
import { useRef, useState } from 'react'

interface UnitCardProps {
  unitId: string
  starLevel?: number
  onClick?: () => void
  disabled?: boolean
  showCost?: boolean
  detailed?: boolean
  baseStats?: {
    hp?: number
    attack?: number
    defense?: number
    attack_speed?: number
    max_mana?: number
    current_mana?: number
  }
  buffedStats?: {
    hp?: number
    attack?: number
    defense?: number
    attack_speed?: number
    max_mana?: number
    current_mana?: number
  }
}

export default function UnitCard({
  unitId,
  starLevel = 1,
  onClick,
  disabled,
  showCost = true,
  detailed = false,
  baseStats,
  buffedStats,
}: UnitCardProps) {
  const unit = getUnit(unitId)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const tooltipRef = useRef<HTMLDivElement | null>(null)
  const [tooltipTop, setTooltipTop] = useState<number | null>(null)

  const getRoleEmoji = (role?: string) => {
    switch (role) {
      case 'defender': return '🛡️'
      case 'fighter': return '⚔️'
      case 'mage': return '🔮'
      case 'duelist': return '🔪'
      default: return ''
    }
  }

  if (!unit) {
    return (
      <div className="p-2 bg-red-900/20 border-2 border-red-500 rounded-lg w-32">
        <p className="text-red-500 text-xs">Unknown: {unitId}</p>
      </div>
    )
  }

  // Use base stats received from backend - no client-side calculation
  const scaledStats = baseStats || (unit.stats ? {
    hp: unit.stats.hp,
    attack: unit.stats.attack,
    defense: unit.stats.defense,
    attack_speed: unit.stats.attack_speed,
    max_mana: (unit as any).stats?.max_mana,
    current_mana: 0,
  } : null)

  const deltas =
    scaledStats && buffedStats
      ? {
          hp: (buffedStats.hp ?? 0) - (scaledStats.hp ?? 0),
          attack: (buffedStats.attack ?? 0) - (scaledStats.attack ?? 0),
          defense: (buffedStats.defense ?? 0) - (scaledStats.defense ?? 0),
          attack_speed: (buffedStats.attack_speed ?? 0) - (scaledStats.attack_speed ?? 0),
          max_mana: (buffedStats.max_mana ?? 0) - ((scaledStats as any).max_mana ?? 0),
        }
      : null

  const displayStats = scaledStats
    ? {
        hp: buffedStats?.hp ?? scaledStats.hp,
        attack: buffedStats?.attack ?? scaledStats.attack,
        defense: buffedStats?.defense ?? scaledStats.defense,
        attack_speed: buffedStats?.attack_speed ?? scaledStats.attack_speed,
        max_mana: buffedStats?.max_mana ?? (scaledStats as any).max_mana ?? 100,
        current_mana: buffedStats?.current_mana ?? (scaledStats as any).current_mana ?? 0,
      }
    : null

  return (
    <div
      ref={containerRef}
      onMouseEnter={() => {
        setTimeout(() => {
          const cont = containerRef.current
          const tip = tooltipRef.current
          if (!cont || !tip) return
          const contRect = cont.getBoundingClientRect()
          const tipHeight = tip.offsetHeight
          const viewportHeight = window.innerHeight
          const margin = 8

          let offset = 0
          const tipBottom = contRect.top + offset + tipHeight
          if (tipBottom > viewportHeight - margin) {
            offset = viewportHeight - margin - contRect.top - tipHeight
          }

          const minOffset = margin - contRect.top
          if (offset < minOffset) offset = minOffset

          setTooltipTop(Math.round(offset))
        }, 10)
      }}
      onMouseLeave={() => setTooltipTop(null)}
      onClick={!disabled ? onClick : undefined}
      className={`relative group w-56 ${onClick && !disabled ? 'cursor-pointer' : ''} ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      }`}
    >
      {(
        <div
          className="hidden group-hover:block absolute p-3 rounded-lg z-[100] shadow-2xl text-xs w-[280px] border-2 pointer-events-none"
          ref={tooltipRef}
          style={{
            backgroundColor: '#0f172a',
            borderColor: getCostBorderColor(unit.cost),
            left: 'calc(100% + 0.5rem)',
            top: tooltipTop !== null ? `${tooltipTop}px` : '0',
            maxHeight: '90vh',
            overflowY: 'auto',
          }}
        >
          <div className="mb-2">
            <div className="font-bold text-sm text-white mb-1">{unit.name}</div>
            <div className="text-gray-400 text-xs mb-2">
              {starLevel > 1 && <span className="text-yellow-400">{'⭐'.repeat(starLevel)} </span>}
              Tier {unit.cost}
              {unit.role && (
                <span 
                  className="ml-2 px-1.5 py-0.5 rounded text-[10px] font-semibold text-white"
                  style={{ backgroundColor: unit.role_color || '#6b7280' }}
                >
                  {unit.role.charAt(0).toUpperCase() + unit.role.slice(1)}
                </span>
              )}
            </div>

            <div className="flex flex-wrap gap-1 mb-2">
              {unit.factions.slice(0, 2).map((faction) => (
                <span key={faction} className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${getFactionColor(faction)} text-white`}>
                  {faction}
                </span>
              ))}
              {unit.classes.slice(0, 2).map((cls) => (
                <span key={cls} className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-purple-600/60 text-white">
                  {cls}
                </span>
              ))}
            </div>
          </div>

          {scaledStats && (
            <div className="space-y-2">
              <div className="flex items-center justify-between py-1">
                <span className="text-red-400 flex items-center gap-1">
                  <span className="text-base">❤️</span>
                  <span className="font-semibold">Życie</span>
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="font-bold text-white text-sm">{displayStats?.hp}</span>
                  {deltas && deltas.hp !== 0 && <span className="text-xs font-semibold text-emerald-400">+{deltas.hp}</span>}
                </div>
              </div>

              <div className="flex items-center justify-between py-1">
                <span className="text-orange-400 flex items-center gap-1">
                  <span className="text-base">⚔️</span>
                  <span className="font-semibold">Atak</span>
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="font-bold text-white text-sm">{displayStats?.attack}</span>
                  {deltas && deltas.attack !== 0 && <span className="text-xs font-semibold text-emerald-400">+{deltas.attack}</span>}
                </div>
              </div>

              <div className="flex items-center justify-between py-1">
                <span className="text-blue-400 flex items-center gap-1">
                  <span className="text-base">🛡️</span>
                  <span className="font-semibold">Obrona</span>
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="font-bold text-white text-sm">{displayStats?.defense}</span>
                  {deltas && deltas.defense !== 0 && <span className="text-xs font-semibold text-emerald-400">+{deltas.defense}</span>}
                </div>
              </div>

              <div className="flex items-center justify-between py-1">
                <span className="text-green-400 flex items-center gap-1">
                  <span className="text-base">⚡</span>
                  <span className="font-semibold">Prędkość ataku</span>
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="font-bold text-white text-sm">{(displayStats?.attack_speed ?? 0).toFixed(2)}</span>
                  {deltas && Math.abs(deltas.attack_speed) > 0.0001 && (
                    <span className="text-xs font-semibold text-emerald-400">+{deltas.attack_speed.toFixed(2)}</span>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between py-1 border-t border-gray-700 pt-2">
                <span className="text-purple-400 flex items-center gap-1">
                  <span className="text-base">🔮</span>
                  <span className="font-semibold">Max Mana</span>
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="font-bold text-white text-sm">{displayStats?.max_mana ?? 100}</span>
                  {deltas && deltas.max_mana !== 0 && <span className="text-xs font-semibold text-emerald-400">+{deltas.max_mana}</span>}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <div
        className={`rounded-lg p-2 transition-all duration-150 border-2 bg-gray-800/90 hover:bg-gray-800 ${detailed ? 'h-64' : 'h-48'} flex flex-col`}
        style={{
          borderColor: getCostBorderColor(unit.cost),
          boxShadow: `0 0 10px ${getCostBorderColor(unit.cost)}40`,
        }}
      >
        <div className="flex justify-center mb-2">
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center font-bold text-2xl border-2 relative overflow-hidden"
            style={{ borderColor: getCostBorderColor(unit.cost), backgroundColor: '#1e293b' }}
          >
            {unit.avatar ? (
              <img
                src={unit.avatar}
                alt={unit.name}
                className="w-full h-full object-cover"
                onError={(e) => {
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

            {showCost && (
              <div
                className="absolute bottom-0 right-0 w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold border"
                style={{ backgroundColor: getCostBorderColor(unit.cost), borderColor: '#1e293b', color: '#000' }}
              >
                {unit.cost}
              </div>
            )}
          </div>
        </div>

        {starLevel > 1 && (
          <div className="flex justify-center mb-1">
            <div className="flex items-center gap-0.5">
              {Array.from({ length: starLevel }).map((_, i) => (
                <span key={i} className="text-yellow-400 text-sm">
                  ⭐
                </span>
              ))}
            </div>
          </div>
        )}

        <h3 className="text-center text-xs font-bold mb-1 truncate px-1 flex items-center justify-center gap-1">{unit.name} <span>{getRoleEmoji(unit.role)}</span></h3>

        <div className="flex flex-wrap gap-0.5 justify-center mb-2 px-1">
          {unit.factions.map((faction) => (
            <span key={faction} className={`px-1 py-0.5 rounded text-[9px] ${getFactionColor(faction)} text-white`}>
              {faction}
            </span>
          ))}
          {unit.classes.map((cls) => (
            <span key={cls} className="px-1 py-0.5 rounded text-[9px] bg-purple-600/60 text-white">
              {cls}
            </span>
          ))}
        </div>

        {scaledStats && detailed && (
          <div className="text-[12px] space-y-1 flex-1 flex flex-col justify-end">
            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-2">
                <span className="text-red-400">❤️</span>
                <span className="text-sm font-semibold">Życie</span>
              </div>
              <span className="font-bold text-sm">{displayStats?.hp}</span>
            </div>

            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-2">
                <span className="text-orange-400">⚔️</span>
                <span className="text-sm font-semibold">Atak</span>
              </div>
              <span className="font-bold text-sm">{displayStats?.attack}</span>
            </div>

            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-2">
                <span className="text-blue-400">🛡️</span>
                <span className="text-sm font-semibold">Obrona</span>
              </div>
              <span className="font-bold text-sm">{displayStats?.defense}</span>
            </div>

            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-2">
                <span className="text-green-400">⚡</span>
                <span className="text-sm font-semibold">Prędkość ataku</span>
              </div>
              <span className="font-bold text-sm">{(displayStats?.attack_speed ?? 0).toFixed(2)}</span>
            </div>

            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-2">
                <span className="text-purple-400">🔮</span>
                <span className="text-sm font-semibold">Mana</span>
              </div>
              <span className="font-bold text-sm">{displayStats?.current_mana ?? 0}/{displayStats?.max_mana ?? 100}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
