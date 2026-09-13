import { useState, useRef, useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { motion } from 'framer-motion'
import { getPassiveTitle, getUnit, type UnitPassive } from '../data/units'
import { useUnitAnchors } from '../hooks/useUnitAnchors'
import type { EffectSummary } from '../hooks/combat/types'
import type { PresentationTrack } from '../hooks/combat/animation/presentationTimeline'
import { combatUnitCardOpponentSizingStyle, combatUnitCardSizingStyle } from './combatUnitCardLayout'
import CombatEffectBadge from './CombatEffectBadge'
import { getCombatTooltipPosition, type CombatTooltipPosition } from './combatTooltipPosition'
import { getCombatImpactDirection } from './combatImpactDirection'

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
  // avatar may be a string or an object like { url }
  avatar?: string | { url?: string }
  skill?: {
    name: string
    description: string
    mana_cost?: number
    effects: any[]
  }
  passive?: UnitPassive
  buffed_stats?: {
    hp?: number
    attack?: number
    defense?: number
    attack_speed?: number
    max_mana?: number
    hp_regen_per_sec?: number
  }
  current_mana?: number
  effects?: EffectSummary[]
}

interface Props {
  unit: Unit
  isOpponent?: boolean
  regen?: { amount_per_sec: number } | undefined
  isActiveAttacker?: boolean
  isActiveTarget?: boolean
  currentTime?: number
  presentationTracks?: PresentationTrack[]
  replayPaused?: boolean
  reducedMotion?: boolean
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

const STATUS_PRESENTATION_INTENTS = new Set([
  'death',
  'buff',
  'heal',
  'shield',
  'effect',
  'passive',
  'item',
  'stun',
  'formation_change',
  'damage_over_time',
  'shield_break',
  'revive',
])

export default function CombatUnitCard({ unit, isOpponent, regen, isActiveAttacker, isActiveTarget, currentTime, presentationTracks = [], replayPaused = false, reducedMotion = false }: Props) {
  const passiveTitle = getPassiveTitle(unit.passive)
  const [showTooltip, setShowTooltip] = useState(false)
  const [tooltipPosition, setTooltipPosition] = useState<CombatTooltipPosition | null>(null)
  const rootRef = useRef<HTMLDivElement | null>(null)
  const { register, getCenter } = useUnitAnchors()

  useEffect(() => {
    register(unit.id, rootRef.current)
    return () => register(unit.id, null)
  }, [unit.id, register])

  const updateTooltipPosition = useCallback(() => {
    const root = rootRef.current
    if (!root) return

    const rect = root.getBoundingClientRect()
    setTooltipPosition(getCombatTooltipPosition(rect, { width: window.innerWidth, height: window.innerHeight }))
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
  const displayMaxHp = unit.buffed_stats?.hp ?? unit.max_hp
  const displayHp = Math.min(unit.hp, displayMaxHp)
  const displayAttack = unit.buffed_stats?.attack ?? unit.attack
  const displayDefense = unit.buffed_stats?.defense ?? unit.defense ?? 0
  const displayAS = unit.buffed_stats?.attack_speed ?? 0
  const displayMaxMana = unit.buffed_stats?.max_mana ?? 100
  const displayMana = unit.current_mana ?? 0
  const rawShield = (unit as Unit & { shield?: number }).shield
  const displayShield = typeof rawShield === 'number' && Number.isFinite(rawShield) ? Math.max(0, rawShield) : 0
  const displayHpRegen = unit.buffed_stats?.hp_regen_per_sec ?? 0
  const activeBorder = isActiveTarget ? '#fb923c' : isActiveAttacker ? '#fde047' : getRarityColor(unit.cost)

  const unitTracks = presentationTracks.filter((track) => track.unitId === unit.id || track.targetId === unit.id)
  const attackTrack = unitTracks.find((track) => track.unitId === unit.id && (track.intent === 'melee_lunge' || track.intent === 'ranged_projectile'))
  const impactTrack = unitTracks.find((track) => track.targetId === unit.id && (track.intent === 'target_recoil' || track.intent === 'shield_hit' || track.intent === 'multi_hit' || track.intent === 'dodge'))
  const statusTrack = unitTracks.find((track) => track.unitId === unit.id && STATUS_PRESENTATION_INTENTS.has(track.intent))
  const impactFallbackDirection = isOpponent ? 'from-bottom' : 'from-top'
  const impactSourceCenter = impactTrack?.unitId && typeof getCenter === 'function'
    ? getCenter(impactTrack.unitId)
    : null
  const targetCenter = typeof getCenter === 'function' ? getCenter(unit.id) : null
  const impactFlashDirection = getCombatImpactDirection(impactSourceCenter, targetCenter, impactFallbackDirection)

  let lungeOffset = { x: 0, y: 0 }
  if (attackTrack && attackTrack.intent === 'melee_lunge' && typeof getCenter === 'function' && rootRef.current) {
    const targetCenter = attackTrack.targetId ? getCenter(attackTrack.targetId) : null
    const rootRect = rootRef.current.getBoundingClientRect()
    if (targetCenter) {
      const origin = { x: rootRect.left + rootRect.width / 2, y: rootRect.top + rootRect.height / 2 }
      const dx = targetCenter.x - origin.x
      const dy = targetCenter.y - origin.y
      const distance = Math.max(1, Math.sqrt(dx * dx + dy * dy))
      const amount = Math.min(84, Math.max(18, distance * 0.18))
      lungeOffset = { x: (dx / distance) * amount, y: (dy / distance) * amount }
    }
  }

  const recoilX = impactTrack?.intent === 'dodge' ? 0 : impactTrack ? -4 : 0
  const recoilY = impactTrack?.intent === 'dodge' ? -3 : impactTrack ? 2 : 0
  const animationDuration = Math.max(0.12, attackTrack?.duration || impactTrack?.duration || statusTrack?.duration || 0.16)
  const presentationAnimation = reducedMotion || replayPaused
    ? { x: 0, y: 0, scale: 1, filter: 'brightness(1)' }
    : attackTrack
      ? {
        x: [0, lungeOffset.x, lungeOffset.x + recoilX, 0],
        y: [0, lungeOffset.y, lungeOffset.y + recoilY, 0],
        scale: [1, 1.04, impactTrack ? 0.98 : 1.02, 1],
        filter: impactTrack?.intent === 'shield_hit' ? ['brightness(1)', 'brightness(1.15)', 'brightness(1)', 'brightness(1)'] : 'brightness(1)',
      }
      : impactTrack
        ? {
          x: [0, recoilX, 0],
          y: [0, recoilY, 0],
          scale: impactTrack.intent === 'shield_hit' ? [1, 1.06, 1] : [1, 0.97, 1],
          filter: impactTrack.intent === 'shield_hit' ? ['brightness(1)', 'brightness(1.25)', 'brightness(1)'] : 'brightness(1)',
        }
        : statusTrack?.intent === 'death'
          ? { x: [0, -3, 0], y: [0, 2, 0], scale: [1, 0.96, 1], filter: 'brightness(1)' }
          : statusTrack
            ? { x: [0, 0], y: [0, -2], scale: [1, 1.03], filter: 'brightness(1.1)' }
            : { x: 0, y: 0, scale: 1, filter: 'brightness(1)' }

  // Resolve avatar source robustly: prefer server-side unit data via getUnit(),
  // then local unit payload, then predictable path.
  const avatarSrc: string = (() => {
    // Determine the canonical template id sent by the backend (units_init should include template_id).
    const possibleTemplateId = (unit as any).template_id || (unit as any).templateId || (unit as any).template?.id || (unit as any).unit_template_id

    try {
      if (possibleTemplateId) {
        const remote = getUnit(possibleTemplateId)
        const remoteAv = (remote as any)?.avatar
        if (typeof remoteAv === 'string' && remoteAv.length > 0) return remoteAv
        if (remoteAv && typeof remoteAv === 'object' && remoteAv.url) return remoteAv.url
        if ((remote as any)?.avatar_url) return (remote as any).avatar_url
      }
    } catch (err) {
      // ignore — getUnit may not be initialized yet
    }

    // Fall back to the data in the combat payload itself
    const avAny = (unit as any).avatar
    if (typeof avAny === 'string' && avAny.length > 0) return avAny
    if (avAny && typeof avAny === 'object' && avAny.url) return avAny.url
    if ((unit as any).avatar_url) return (unit as any).avatar_url

    // Fallback to a predictable path based on template id (if present) or instance id
    const idForPath = possibleTemplateId || unit.id
    return `/avatars/${idForPath}.png`
  })()

  return (
    <motion.div
      ref={rootRef}
      className="combat-unit-card group"
      initial={false}
      animate={presentationAnimation}
      transition={{ duration: animationDuration, ease: 'easeOut', times: attackTrack ? [0, 0.42, 0.62, 1] : undefined }}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => {
        if (document.activeElement !== rootRef.current) setShowTooltip(false)
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
      tabIndex={0}
      role="button"
      aria-expanded={showTooltip}
      aria-label={`Jednostka bojowa: ${unit.name}`}
      style={{
        backgroundColor: '#0f172a',
        borderRadius: isOpponent ? '0.25rem' : '0.5rem',
        padding: isOpponent ? combatUnitCardOpponentSizingStyle.padding : combatUnitCardSizingStyle.padding,
        border: `2px solid ${unit.hp > 0 ? activeBorder : '#374151'}`,
        opacity: unit.hp > 0 ? 1 : 0.4,
        transition: 'all 0.3s',
        boxShadow: unit.hp > 0
          ? isActiveTarget
            ? '0 0 0 2px rgba(251, 146, 60, 0.45), 0 0 18px rgba(251, 146, 60, 0.18)'
            : isActiveAttacker
              ? '0 0 0 2px rgba(250, 204, 21, 0.45), 0 0 18px rgba(250, 204, 21, 0.18)'
              : `0 0 10px ${getRarityColor(unit.cost)}40`
          : 'none',
        minWidth: 0,
        position: 'relative',
        width: combatUnitCardSizingStyle.width,
        flexShrink: 0,
        willChange: 'transform, filter',
      }}
    >
      {/* Active effect badges */}
      <div className="combat-unit-card-badges" style={{ position: 'absolute', top: '6px', right: '6px', display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', gap: '6px', maxWidth: 'calc(100% - 12px)', zIndex: 40 }}>
        {(unit.effects || []).map((effect, idx) => (
          <CombatEffectBadge key={`${effect.id || effect.type}-${idx}`} effect={effect} currentTime={currentTime} index={idx} />
        ))}
      </div>
      {impactTrack && !replayPaused && (
        <motion.div
          key={impactTrack.id}
          className={`combat-unit-impact-flash combat-unit-impact-flash-${impactTrack.intent}`}
          data-impact-intent={impactTrack.intent}
          data-impact-direction={impactFlashDirection}
          aria-hidden="true"
          initial={{ opacity: reducedMotion ? 0.55 : 0, scale: reducedMotion ? 1 : 0.96 }}
          animate={reducedMotion
            ? { opacity: 0.55, scale: 1 }
            : { opacity: [0, 0.9, 0], scale: [0.96, 1.04, 1] }}
          transition={{ duration: reducedMotion ? 0.08 : Math.max(0.12, animationDuration), ease: 'easeOut' }}
        />
      )}
      {statusTrack && !replayPaused && (
        <motion.div
          key={statusTrack.id}
          className={`combat-unit-status-flash combat-unit-status-flash-${statusTrack.intent}`}
          data-status-intent={statusTrack.intent}
          aria-hidden="true"
          initial={{ opacity: reducedMotion ? 0.55 : 0, scale: reducedMotion ? 1 : 0.96 }}
          animate={reducedMotion
            ? { opacity: 0.55, scale: 1 }
            : { opacity: [0, 0.72, 0], scale: [0.96, 1.03, 1] }}
          transition={{ duration: reducedMotion ? 0.08 : Math.max(0.12, animationDuration), ease: 'easeOut' }}
        />
      )}
      {/* Old inline attack/skill/target visuals removed in favor of projectile VFX */}

      {/* Unit avatar (robust source resolution with fallback) */}
      <img
        src={avatarSrc}
        alt={unit.name}
        className="combat-unit-avatar"
        style={{ width: '100%', height: combatUnitCardSizingStyle.avatarHeight, objectFit: 'cover', borderRadius: '0.25rem', marginBottom: '0.25rem' }}
        onError={(e: any) => {
          // Fallback to generic avatar if specific file missing
          if (e?.currentTarget && e.currentTarget.src && !e.currentTarget.src.endsWith('/avatars/default.png')) {
            e.currentTarget.src = '/avatars/default.png'
          }
        }}
      />

      <div className="combat-unit-card-name text-xs font-bold text-white mb-1 text-center truncate">
        {unit.name} ⭐{unit.star_level}
      </div>

      {unit.factions && unit.factions.length > 0 && !isOpponent && (
        <div className="combat-unit-card-factions flex flex-wrap gap-1 justify-center mb-1">
          {unit.factions.slice(0, 2).map((f) => (
            <span key={f} className="text-[9px] px-1 py-0.5 bg-blue-500/30 rounded text-blue-200">
              {f}
            </span>
          ))}
        </div>
      )}

      <div
        className="combat-unit-card-bar relative h-2 bg-gray-700 rounded-full overflow-hidden border border-gray-600"
        style={{ height: combatUnitCardSizingStyle.barHeight }}
        role="progressbar"
        aria-label={`HP ${Math.round(displayHp)} of ${Math.round(displayMaxHp)}`}
        aria-valuemin={0}
        aria-valuemax={Math.round(displayMaxHp)}
        aria-valuenow={Math.round(displayHp)}
      >
        <div
          className="absolute inset-y-0 left-0"
          style={{
            width: `${displayMaxHp > 0 ? (displayHp / displayMaxHp) * 100 : 0}%`,
            background: `linear-gradient(to right, ${getRarityColor(unit.cost)}, ${getRarityColor(unit.cost)}dd)`,
          }}
        />
      </div>

      <div
        className="combat-unit-card-bar combat-unit-card-mana-bar relative h-2 bg-gray-700 rounded-full overflow-hidden border border-gray-600 mt-1"
        style={{ height: combatUnitCardSizingStyle.barHeight, marginTop: combatUnitCardSizingStyle.barGap }}
        role="progressbar"
        aria-label={`Mana ${Math.round(displayMana)} of ${Math.round(displayMaxMana)}`}
        aria-valuemin={0}
        aria-valuemax={Math.round(displayMaxMana)}
        aria-valuenow={Math.round(displayMana)}
      >
        <div
          className="absolute inset-y-0 left-0"
          style={{
            width: `${displayMaxMana > 0 ? (displayMana / displayMaxMana) * 100 : 0}%`,
            background: 'linear-gradient(to right, #8b5cf6, #a855f7)',
          }}
        />
      </div>

      <div className="combat-unit-card-vitals" aria-label={`Combat stats for ${unit.name}`}>
        <div className="combat-unit-card-vital" data-combat-vital="hp">
          <span className="combat-unit-card-vital-label">HP</span>
          <strong>{Math.round(displayHp)}/{Math.round(displayMaxHp)}</strong>
        </div>
        <div className="combat-unit-card-vital" data-combat-vital="mana">
          <span className="combat-unit-card-vital-label">Mana</span>
          <strong>{Math.round(displayMana)}/{Math.round(displayMaxMana)}</strong>
        </div>
        <div className="combat-unit-card-vital" data-combat-vital="shield">
          <span className="combat-unit-card-vital-label">Shield</span>
          <strong>{Math.round(displayShield)}</strong>
        </div>
      </div>

      {/* Tooltip is portaled so the board/frame overflow cannot clip it. */}
      {showTooltip && tooltipPosition && typeof document !== 'undefined' && createPortal(
        <div
          data-combat-unit-tooltip={unit.id}
          className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg p-4 shadow-xl"
          style={{
            position: 'fixed',
            left: tooltipPosition.left,
            top: tooltipPosition.top,
            width: 320,
            maxWidth: 'calc(100vw - 16px)',
            maxHeight: 'min(360px, calc(100vh - 16px))',
            boxSizing: 'border-box',
            overflowY: 'auto',
            zIndex: 1100,
            pointerEvents: 'none',
          }}
          role="tooltip"
        >
          <div className="flex items-center mb-3">
            {unit.avatar && (
              <img src={typeof unit.avatar === 'string' ? unit.avatar : (unit as any)?.avatar?.url || ''} alt={unit.name} className="w-10 h-10 rounded mr-3 object-cover" />
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
          {unit.passive?.description && (
            <div className="mb-3 rounded border border-amber-500/40 bg-amber-500/10 p-2 text-xs text-amber-100">
              {passiveTitle && <div className="mb-1 font-semibold text-amber-300">{passiveTitle}</div>}
              <div>{unit.passive.description}</div>
            </div>
          )}
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div>❤️ HP: {Math.round(displayHp)}/{Math.round(displayMaxHp)}</div>
            <div>⚔️ ATK: {Math.round(displayAttack)}</div>
            <div>🛡️ DEF: {Math.round(displayDefense)}</div>
            <div>⚡ SPD: {displayAS.toFixed(2)}</div>
            <div>🔮 Mana: {Math.round(displayMana)}/{Math.round(displayMaxMana)}</div>
            {displayHpRegen > 0 && <div>💚 Regen: +{Math.round(displayHpRegen)}/s</div>}
          </div>
          {/* Arrow */}
          <div
            className="absolute left-1/2 transform -translate-x-1/2 w-0 h-0"
            style={tooltipPosition.placement === 'above'
              ? { top: '100%', borderLeft: '4px solid transparent', borderRight: '4px solid transparent', borderTop: '4px solid #1f2937' }
              : { bottom: '100%', borderLeft: '4px solid transparent', borderRight: '4px solid transparent', borderBottom: '4px solid #1f2937' }}
          />
        </div>,
        document.body,
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
    </motion.div>
  )
}
