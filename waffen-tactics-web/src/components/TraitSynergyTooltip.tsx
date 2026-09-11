import { createPortal } from 'react-dom'
import { useCallback, useEffect, useRef, useState } from 'react'
import { getTraitColor, getTraitDescription, getTraitEffectPresentation } from '../hooks/combatOverlayUtils'
import { getAllUnits, getCostBorderColor } from '../data/units'
import { getCombatTooltipPosition, type CombatTooltipPosition } from './combatTooltipPosition'

interface Props {
  traitName: string
  data: any
  traitData?: any
}

const TOOLTIP_SIZE = { width: 360, height: 620 }

export default function TraitSynergyTooltip({ traitName, data, traitData }: Props) {
  const [showTooltip, setShowTooltip] = useState(false)
  const [tooltipPosition, setTooltipPosition] = useState<CombatTooltipPosition | null>(null)
  const triggerRef = useRef<HTMLDivElement | null>(null)
  const isActive = data.tier > 0
  const color = isActive ? getTraitColor(data.tier) : '#6b7280'
  const opacity = isActive ? 1 : 0.5

  const updateTooltipPosition = useCallback(() => {
    const trigger = triggerRef.current
    if (!trigger || typeof window === 'undefined') return

    setTooltipPosition(getCombatTooltipPosition(trigger.getBoundingClientRect(), {
      width: window.innerWidth,
      height: window.innerHeight,
    }, TOOLTIP_SIZE))
  }, [])

  useEffect(() => {
    if (!showTooltip) return

    updateTooltipPosition()
    window.addEventListener('resize', updateTooltipPosition)
    window.addEventListener('scroll', updateTooltipPosition, true)

    return () => {
      window.removeEventListener('resize', updateTooltipPosition)
      window.removeEventListener('scroll', updateTooltipPosition, true)
    }
  }, [showTooltip, updateTooltipPosition])

  return (
    <div
      ref={triggerRef}
      className="relative"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => {
        if (document.activeElement !== triggerRef.current) setShowTooltip(false)
      }}
      onFocus={() => setShowTooltip(true)}
      onBlur={() => setShowTooltip(false)}
      onClick={() => setShowTooltip(current => !current)}
      onKeyDown={event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          setShowTooltip(current => !current)
        }
      }}
      role="button"
      tabIndex={0}
      aria-expanded={showTooltip}
      aria-label={`${traitName}, ${data.count} jednostek${isActive ? `, Tier ${data.tier}` : ''}`}
    >
      <div
        style={{
          backgroundColor: `${color}30`,
          borderColor: color,
          color: color,
          opacity: opacity,
        }}
        className="rounded px-3 py-1 text-xs border-2 font-bold cursor-pointer transition-all hover:opacity-100 hover:scale-105"
      >
        {traitName} [{data.count}]{isActive && ` T${data.tier}`}
      </div>

      {traitData && showTooltip && tooltipPosition && typeof document !== 'undefined' && createPortal(
        <div
          data-trait-tooltip
          data-tooltip-placement={tooltipPosition.placement}
          role="tooltip"
          style={{
            backgroundColor: '#1e293b',
            border: `2px solid ${color}`,
            color: '#e2e8f0',
            position: 'fixed',
            left: tooltipPosition.left,
            top: tooltipPosition.top,
            width: TOOLTIP_SIZE.width,
            maxWidth: 'calc(100vw - 16px)',
            maxHeight: 'min(620px, calc(100vh - 16px))',
            boxSizing: 'border-box',
            overflowY: 'auto',
            overflowWrap: 'anywhere',
            zIndex: 1100,
            pointerEvents: 'none',
          }}
          className="p-3 rounded-md shadow-xl text-xs"
        >
          <div className="font-bold text-sm mb-1" style={{ color: color }}>{traitName}</div>
          {traitData.description && (
            <div className="text-gray-300 mb-2 text-xs leading-relaxed">{traitData.description}</div>
          )}

          <div className="border-t border-gray-600 pt-2 mt-2">
            <div className="text-gray-400 text-xs mb-1">Progi aktywacji:</div>
            {(traitData.thresholds || []).map((threshold: number, idx: number) => {
              const tierNum = idx + 1
              const tierIsActive = data.tier >= tierNum
              const isCurrent = data.tier === tierNum
              const tierColor = getTraitColor(tierNum)

              return (
                <div
                  key={idx}
                  className="flex items-start gap-2 mb-1.5 text-xs"
                  style={{
                    opacity: tierIsActive ? 1 : 0.6,
                    color: tierIsActive ? tierColor : '#9ca3af',
                  }}
                >
                  <span className="font-mono font-bold">
                    {tierIsActive ? '✅' : isCurrent ? '⏩' : '⬜'}
                  </span>
                  <div className="flex-1">
                    <div className="font-bold">[{threshold}] Tier {tierNum}</div>
                    <div className="text-xs mt-0.5" style={{ color: tierIsActive ? '#d1d5db' : '#9ca3af' }}>
                      {getTraitDescription(traitData, tierNum)}
                    </div>
                    {getTraitEffectPresentation(traitData, tierNum).map((effect, effectIndex) => (
                      <div key={`${tierNum}-${effectIndex}`} data-trait-effect-details className="mt-1 rounded border border-gray-600/70 bg-black/10 p-1.5 text-[11px] leading-snug">
                        <div><span className="text-gray-400">Trigger:</span> {effect.trigger}</div>
                        <div><span className="text-gray-400">Cel:</span> {effect.target}</div>
                        <div><span className="text-gray-400">Czas:</span> {effect.duration}</div>
                        <div><span className="text-gray-400">Odświeżanie:</span> {effect.refresh}</div>
                        <div><span className="text-gray-400">Stackowanie:</span> {effect.stacking}</div>
                        {effect.conditions.map(condition => <div key={condition}><span className="text-gray-400">Warunek:</span> {condition}</div>)}
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>

          <div className="border-t border-gray-600 pt-2 mt-2 text-xs">
            <span className="text-gray-400">Status: </span>
            <span style={{ color: isActive ? '#10b981' : '#ef4444', fontWeight: 'bold' }}>
              {isActive
                ? `✓ Tier ${data.tier} Aktywny (${data.count} jednostek)`
                : `✗ Nieaktywny (${data.count}/${traitData?.thresholds?.[0] || 0} jednostek)`
              }
            </span>
          </div>

          <div style={{ marginTop: 8, display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
            {(() => {
              try {
                const all = getAllUnits()
                const unitsForTrait = all.filter(u => (u.factions || []).includes(traitName) || (u.classes || []).includes(traitName))
                return unitsForTrait.slice(0, 12).map(u => (
                  <img
                    key={u.id}
                    src={u.avatar || '/avatars/default.png'}
                    title={u.name}
                    alt={u.name}
                    style={{ width: 34, height: 34, borderRadius: '9999px', objectFit: 'cover', border: `2px solid ${getCostBorderColor(u.cost || 1)}` }}
                  />
                ))
              } catch (e) {
                return null
              }
            })()}
          </div>
        </div>,
        document.body,
      )}
    </div>
  )
}
