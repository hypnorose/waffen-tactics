import { getUnit, getCostBorderColor, getFactionColor, getPassiveTitle } from '../data/units'
import { createPortal } from 'react-dom'
import { useCallback, useLayoutEffect, useRef, useState, useId } from 'react'
import type { CombatUnitRoundStats } from '../hooks/combat/types'
import EquippedItems from './EquippedItems'
import { formatItemStat, formatItemTrigger, getItemMechanicDescription, ITEM_ICONS, type Item, type ItemUnitPreview } from '../data/items'
import ItemPreviewTooltip from './ItemPreviewTooltip'
import { ItemUnitPreviewContent } from './ItemPreviewContent'
import { boardUnitCardSizingStyle } from './combatUnitCardLayout'
import { getItemTooltipPosition, type ItemTooltipPosition } from './itemTooltipPosition'

interface UnitCardProps {
  unitId: string
  starLevel?: number
  onClick?: () => void
  disabled?: boolean
  showCost?: boolean
  detailed?: boolean
  isDragging?: boolean
  position?: 'front' | 'back'
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
  lastRoundStats?: CombatUnitRoundStats
  items?: string[]
  itemCatalog?: Item[]
  itemPreview?: ItemUnitPreview
  boardLayout?: boolean
}

export default function UnitCard({
  unitId,
  starLevel = 1,
  onClick,
  disabled,
  showCost = true,
  detailed = false,
  isDragging = false,
  position,
  baseStats,
  buffedStats,
  lastRoundStats,
  items,
  itemCatalog = [],
  itemPreview,
  boardLayout = false,
}: UnitCardProps) {
  const unit = getUnit(unitId)
  const itemById = new Map(itemCatalog.map(item => [item.id, item]))
  const hasEquippedItems = Boolean(items?.length)
  const passiveTitle = getPassiveTitle(unit?.passive)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const tooltipRef = useRef<HTMLDivElement | null>(null)
  const [showUnitTooltip, setShowUnitTooltip] = useState(false)
  const [tooltipPosition, setTooltipPosition] = useState<ItemTooltipPosition | null>(null)
  const tooltipId = useId()

  const closeUnitTooltip = () => {
    setShowUnitTooltip(false)
    setTooltipPosition(null)
  }

  const updateTooltipPosition = useCallback(() => {
    const anchor = containerRef.current
    if (!anchor || typeof window === 'undefined') return

    const measuredTooltip = tooltipRef.current?.getBoundingClientRect()
    setTooltipPosition(getItemTooltipPosition(
      anchor.getBoundingClientRect(),
      { width: window.innerWidth, height: window.innerHeight },
      measuredTooltip
        ? { width: measuredTooltip.width, height: measuredTooltip.height }
        : { width: 240, height: 460 },
    ))
  }, [])

  const openUnitTooltip = () => {
    if (isDragging) return
    setShowUnitTooltip(true)
  }

  useLayoutEffect(() => {
    if (!showUnitTooltip) return

    // The portal is mounted before this layout effect runs, so the second
    // measurement uses the real long-content height instead of a guess.
    updateTooltipPosition()
    window.addEventListener('resize', updateTooltipPosition)
    window.addEventListener('scroll', updateTooltipPosition, true)
    return () => {
      window.removeEventListener('resize', updateTooltipPosition)
      window.removeEventListener('scroll', updateTooltipPosition, true)
    }
  }, [showUnitTooltip, updateTooltipPosition])

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
      onMouseEnter={openUnitTooltip}
      onMouseLeave={() => {
        if (document.activeElement !== containerRef.current) closeUnitTooltip()
      }}
      onTouchStart={openUnitTooltip}
      onFocus={openUnitTooltip}
      onBlur={closeUnitTooltip}
      onClick={!disabled ? () => {
        openUnitTooltip()
        onClick?.()
      } : undefined}
      onKeyDown={event => {
        if (!disabled && (event.key === 'Enter' || event.key === ' ')) {
          event.preventDefault()
          setShowUnitTooltip(current => !current)
          onClick?.()
        }
      }}
      tabIndex={disabled ? -1 : 0}
      role="button"
      aria-label={`Jednostka: ${unit.name}`}
      aria-describedby={showUnitTooltip ? tooltipId : undefined}
      aria-expanded={showUnitTooltip}
      data-board-unit-card={boardLayout ? 'true' : undefined}
      className={`relative group ${boardLayout ? 'w-full' : detailed ? 'w-56' : 'w-36'} select-none ${boardLayout ? `${detailed ? 'board-unit-card-detailed' : 'board-unit-card'}` : ''} ${onClick && !disabled ? 'cursor-pointer' : ''} ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      }`}
      style={boardLayout ? { height: detailed ? boardUnitCardSizingStyle.detailedHeight : boardUnitCardSizingStyle.compactHeight } : undefined}
    >
      <ItemPreviewTooltip anchorRef={containerRef} open={Boolean(itemPreview)}>
        {itemPreview && <ItemUnitPreviewContent preview={itemPreview} itemCatalog={itemCatalog} />}
      </ItemPreviewTooltip>
      {showUnitTooltip && tooltipPosition && typeof document !== 'undefined' && createPortal(
        <div
          id={tooltipId}
          data-unit-tooltip={unit.id}
          className="p-3 rounded-lg shadow-2xl text-xs border-2 pointer-events-none text-left"
          ref={tooltipRef}
          role="tooltip"
          style={{
            backgroundColor: '#0f172a',
            borderColor: getCostBorderColor(unit.cost),
            position: 'fixed',
            left: tooltipPosition.left,
            top: tooltipPosition.top,
            width: 240,
            maxWidth: 'calc(100vw - 16px)',
            maxHeight: 'min(90vh, calc(100vh - 16px))',
            boxSizing: 'border-box',
            overflowY: 'auto',
            overflowWrap: 'anywhere',
            zIndex: 2000,
          }}
        >
          <div className="mb-2">
            <div className="font-bold text-sm text-white mb-1">{unit.name}</div>
            {position && (
              <div className="text-xs text-gray-300 mb-1">
                Pozycja: <span className={position === 'front' ? 'text-red-400' : 'text-blue-400'}>
                  {position === 'front' ? '⚔️ Frontowa' : '🛡️ Tylna'}
                </span>
              </div>
            )}
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
            {unit.passive?.description && (
              <div className="mb-2 rounded border border-amber-500/40 bg-amber-500/10 p-2 text-xs text-amber-100">
                {passiveTitle && <div className="mb-1 font-semibold text-amber-300">{passiveTitle}</div>}
                <div>{unit.passive.description}</div>
              </div>
            )}
            {items && items.length > 0 && (
              <div className="mb-2 rounded border border-amber-300/40 bg-amber-500/10 p-2 text-xs text-slate-100">
                <div className="mb-1 font-semibold text-amber-300">Wyposażenie</div>
                <div className="space-y-2">
                  {items.slice(0, 3).map((itemId, index) => {
                    const item = itemById.get(itemId)
                    const mechanicDescription = item ? getItemMechanicDescription(item) : undefined
                    return <div key={`${itemId}-${index}`} className="border-b border-slate-700/70 pb-1 last:border-0 last:pb-0">
                      <div className={`font-semibold ${item ? 'text-amber-100' : 'text-red-200'}`}>{ITEM_ICONS[itemId] || '◆'} {item?.name || `Nieznany przedmiot: ${itemId}`}</div>
                      {item && <div className="text-emerald-200">{Object.entries(item.stats).map(([stat, value]) => formatItemStat(stat, value)).join(', ')}</div>}
                      {mechanicDescription && <div className="text-slate-300">{mechanicDescription}</div>}
                      {item?.effect && <div className="text-cyan-200">Aktywacja: {formatItemTrigger(item.effect.trigger)}{item.effect.duration !== null ? ` · ${item.effect.duration} s` : ''}</div>}
                    </div>
                  })}
                </div>
              </div>
            )}
          </div>

            {scaledStats && (
            <div className="space-y-2">
              <div className="flex items-center justify-between py-1">
                <span className="text-red-400 flex items-center gap-1">
                  <span className="text-base">❤️</span>
                  <span className="font-semibold">Życie</span>
                </span>
                <div className="flex items-baseline gap-2">
                  {deltas && deltas.hp !== 0 ? (
                    <span className="font-bold text-white text-sm">
                      {Math.round(scaledStats?.hp ?? 0)} + <span className="text-green-400">{Math.round(deltas.hp)}</span> = <span className="text-green-400">{Math.round(displayStats?.hp ?? 0)}</span>
                    </span>
                  ) : (
                    <span className="font-bold text-white text-sm">{Math.round(displayStats?.hp ?? 0)}</span>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between py-1">
                <span className="text-orange-400 flex items-center gap-1">
                  <span className="text-base">⚔️</span>
                  <span className="font-semibold">Atak</span>
                </span>
                <div className="flex items-baseline gap-2">
                  {deltas && deltas.attack !== 0 ? (
                    <span className="font-bold text-white text-sm">
                      {Math.round(scaledStats?.attack ?? 0)} + <span className="text-green-400">{Math.round(deltas.attack)}</span> = <span className="text-green-400">{Math.round(displayStats?.attack ?? 0)}</span>
                    </span>
                  ) : (
                    <span className="font-bold text-white text-sm">{Math.round(displayStats?.attack ?? 0)}</span>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between py-1">
                <span className="text-blue-400 flex items-center gap-1">
                  <span className="text-base">🛡️</span>
                  <span className="font-semibold">Obrona</span>
                </span>
                <div className="flex items-baseline gap-2">
                  {deltas && deltas.defense !== 0 ? (
                    <span className="font-bold text-white text-sm">
                      {Math.round(scaledStats?.defense ?? 0)} + <span className="text-green-400">{Math.round(deltas.defense)}</span> = <span className="text-green-400">{Math.round(displayStats?.defense ?? 0)}</span>
                    </span>
                  ) : (
                    <span className="font-bold text-white text-sm">{Math.round(displayStats?.defense ?? 0)}</span>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between py-1">
                <span className="text-green-400 flex items-center gap-1">
                  <span className="text-base">⚡</span>
                  <span className="font-semibold">Prędkość ataku</span>
                </span>
                <div className="flex items-baseline gap-2">
                  {deltas && Math.abs(deltas.attack_speed) > 0.0001 ? (
                    <span className="font-bold text-white text-sm">
                      {(scaledStats?.attack_speed ?? 0).toFixed(2)} + <span className="text-green-400">{(Math.round(deltas.attack_speed * 100) / 100).toFixed(2)}</span> = <span className="text-green-400">{(displayStats?.attack_speed ?? 0).toFixed(2)}</span>
                    </span>
                  ) : (
                    <span className="font-bold text-white text-sm">{(displayStats?.attack_speed ?? 0).toFixed(2)}</span>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between py-1 border-t border-gray-700 pt-2">
                <span className="text-purple-400 flex items-center gap-1">
                  <span className="text-base">🔮</span>
                  <span className="font-semibold">Max Mana</span>
                </span>
                <div className="flex items-baseline gap-2">
                  {deltas && deltas.max_mana !== 0 ? (
                    <span className="font-bold text-white text-sm">
                      {Math.round((scaledStats as any)?.max_mana ?? 100)} + <span className="text-green-400">{Math.round(deltas.max_mana)}</span> = <span className="text-green-400">{Math.round(displayStats?.max_mana ?? 100)}</span>
                    </span>
                  ) : (
                    <span className="font-bold text-white text-sm">{Math.round(displayStats?.max_mana ?? 100)}</span>
                  )}
                </div>
              </div>
            </div>
          )}
          {lastRoundStats?.participated && (
            <div className="mt-2 border-t border-slate-700 pt-2 text-[11px] text-slate-200">
              <div className="mb-1 font-semibold text-slate-400">Ostatnia runda</div>
              <div className="flex items-center justify-between">
                <span className="text-orange-300">Śr. DPS</span>
                <span className="font-bold text-orange-200">{lastRoundStats.avg_dps.toFixed(1)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-red-300">Przyjęte/s</span>
                <span className="font-bold text-red-200">{lastRoundStats.avg_damage_received.toFixed(1)}</span>
              </div>
            </div>
          )}
          <div
            className="absolute left-1/2 -translate-x-1/2 w-0 h-0"
            style={tooltipPosition.placement === 'above'
              ? { top: '100%', borderLeft: '4px solid transparent', borderRight: '4px solid transparent', borderTop: `4px solid ${getCostBorderColor(unit.cost)}` }
              : { bottom: '100%', borderLeft: '4px solid transparent', borderRight: '4px solid transparent', borderBottom: `4px solid ${getCostBorderColor(unit.cost)}` }}
          />
        </div>,
        document.body,
      )}

      <div
          className={`${boardLayout ? 'board-unit-card-shell' : ''} w-full rounded-lg ${detailed ? 'p-2' : 'p-1'} transition-all duration-150 border-2 bg-gray-800/90 hover:bg-gray-800 ${boardLayout ? '' : `${detailed ? (hasEquippedItems ? 'min-h-72' : 'min-h-64') : (hasEquippedItems ? 'min-h-40' : 'min-h-36')} h-auto`} flex flex-col relative`}
        style={{
          borderColor: getCostBorderColor(unit.cost),
          boxShadow: `0 0 10px ${getCostBorderColor(unit.cost)}40`,
        }}
      >
        {starLevel > 1 && (
          <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10">
            <div className="flex items-center gap-0.5 px-1 py-0.5">
              {Array.from({ length: starLevel }).map((_, i) => (
                <span key={i} className="text-yellow-400 text-sm bg-black/70 px-0.5 py-0.5 rounded-full">
                  ⭐
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="flex shrink-0 justify-center mb-2">
          <div
            className={`${detailed ? 'w-48 h-24' : 'w-28 h-14'} rounded-lg flex items-center justify-center font-bold text-2xl border-2 relative overflow-hidden`}
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
              <span className={detailed ? 'text-3xl' : 'text-xl'}>👤</span>
            )}

            {showCost && (
              <div
                className={`absolute bottom-0 right-0 ${detailed ? 'w-6 h-6' : 'w-4 h-4'} rounded-full flex items-center justify-center text-[10px] font-bold border`}
                style={{ backgroundColor: getCostBorderColor(unit.cost), borderColor: '#1e293b', color: '#000' }}
              >
                {unit.cost}
              </div>
            )}
          </div>
        </div>

        <h3
          title={unit.name}
          aria-label={`Jednostka: ${unit.name}`}
          className={`min-w-0 shrink-0 text-center text-xs font-bold ${detailed ? 'mb-1' : 'mb-0.5'} px-1 flex items-center justify-center gap-1 ${detailed ? '' : 'text-[9px]'}`}
        >
          <span className="min-w-0 truncate">{unit.name}</span>
          <span className="shrink-0">{getRoleEmoji(unit.role)}</span>
        </h3>

        <div className={`flex shrink-0 flex-wrap gap-0.5 justify-center mb-2 px-1 ${boardLayout ? 'board-unit-card-faction-slot' : ''}`} aria-hidden={boardLayout && unit.factions.length === 0 && unit.classes.length === 0 ? true : undefined}>
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

        {boardLayout ? (
          <div className="board-unit-card-items-slot" aria-hidden={!hasEquippedItems}>
            <EquippedItems itemIds={items} itemCatalog={itemCatalog} />
          </div>
        ) : (
          <div className="shrink-0">
            <EquippedItems itemIds={items} itemCatalog={itemCatalog} />
          </div>
        )}

        {!detailed && (boardLayout ? (
          <div className="board-unit-card-stats-slot flex items-center justify-center gap-2 border-t border-slate-700/80 pt-1 text-[9px] leading-none" aria-hidden={!lastRoundStats?.participated}>
            {lastRoundStats?.participated && (
              <>
                <span className="text-orange-300" title="Średni DPS z ostatniej rundy">DPS {lastRoundStats.avg_dps.toFixed(1)}</span>
                <span className="text-red-300" title="Średnie przyjęte obrażenia na sekundę">-HP/s {lastRoundStats.avg_damage_received.toFixed(1)}</span>
              </>
            )}
          </div>
        ) : lastRoundStats?.participated ? (
          <div className="flex items-center justify-center gap-2 border-t border-slate-700/80 pt-1 text-[9px] leading-none">
            <span className="text-orange-300" title="Średni DPS z ostatniej rundy">DPS {lastRoundStats.avg_dps.toFixed(1)}</span>
            <span className="text-red-300" title="Średnie przyjęte obrażenia na sekundę">-HP/s {lastRoundStats.avg_damage_received.toFixed(1)}</span>
          </div>
        ) : null)}

        {scaledStats && detailed && (
          <div className="text-[10px] space-y-0.5 flex-1 flex flex-col justify-end">
            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-1">
                <span className="text-red-400 text-xs">❤️</span>
                <span className="text-xs font-semibold">Życie</span>
              </div>
              <span className="font-bold text-xs">{displayStats?.hp}</span>
            </div>

            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-1">
                <span className="text-orange-400 text-xs">⚔️</span>
                <span className="text-xs font-semibold">Atak</span>
              </div>
              <span className="font-bold text-xs">{displayStats?.attack}</span>
            </div>

            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-1">
                <span className="text-blue-400 text-xs">🛡️</span>
                <span className="text-xs font-semibold">Obrona</span>
              </div>
              <span className="font-bold text-xs">{displayStats?.defense}</span>
            </div>

            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-1">
                <span className="text-green-400 text-xs">⚡</span>
                <span className="text-xs font-semibold">Prędkość ataku</span>
              </div>
              <span className="font-bold text-xs">{(displayStats?.attack_speed ?? 0).toFixed(2)}</span>
            </div>

            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-1">
                <span className="text-purple-400 text-xs">🔮</span>
                <span className="text-xs font-semibold">Mana</span>
              </div>
              <span className="font-bold text-xs">{displayStats?.current_mana ?? 0}/{displayStats?.max_mana ?? 100}</span>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
