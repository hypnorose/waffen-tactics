import { useState, useRef, useEffect } from 'react'
import { getUnit } from '../data/units'
import { useUnitAnchors } from '../hooks/useUnitAnchors'
import type { CombatUnitRoundStats } from '../hooks/combat/types'

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
  passive?: {
    description: string
    [key: string]: any
  }
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
  regen?: { amount_per_sec: number } | undefined
  isActiveAttacker?: boolean
  isActiveTarget?: boolean
  roundStats?: CombatUnitRoundStats
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

export default function CombatUnitCard({ unit, isOpponent, regen, isActiveAttacker, isActiveTarget, roundStats }: Props) {
  const [showTooltip, setShowTooltip] = useState(false)
  const rootRef = useRef<HTMLDivElement | null>(null)
  const { register } = useUnitAnchors()

  useEffect(() => {
    register(unit.id, rootRef.current)
    return () => register(unit.id, null)
  }, [unit.id, register])
  const displayMaxHp = unit.buffed_stats?.hp ?? unit.max_hp
  const displayHp = Math.min(unit.hp, displayMaxHp)
  const displayAttack = unit.buffed_stats?.attack ?? unit.attack
  const displayDefense = unit.buffed_stats?.defense ?? unit.defense ?? 0
  const displayAS = unit.buffed_stats?.attack_speed ?? 0
  const displayMaxMana = unit.buffed_stats?.max_mana ?? 100
  const displayMana = unit.current_mana ?? 0
  const displayHpRegen = unit.buffed_stats?.hp_regen_per_sec ?? 0
  const hasBonusReady = unit.hp > 0 && displayMaxMana > 0 && displayMana >= displayMaxMana
  const activeBorder = isActiveTarget ? '#fb923c' : isActiveAttacker ? '#fde047' : getRarityColor(unit.cost)

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
    <div
      ref={rootRef}
      className="group"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      style={{
        backgroundColor: '#0f172a',
        borderRadius: isOpponent ? '0.25rem' : '0.5rem',
        padding: isOpponent ? '0.25rem' : '0.5rem',
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
        width: '120px',
        flexShrink: 0,
      }}
    >
      {/* Active effect badges */}
      <div style={{ position: 'absolute', top: '6px', right: '6px', display: 'flex', gap: '6px', zIndex: 40 }}>
        {(unit as any).effects && (unit as any).effects.slice(0,3).map((eff: any, idx: number) => {
          const key = eff.id || `${unit.id}_eff_${idx}`
          let label = ''
          let bg = 'rgba(255,255,255,0.06)'
          if (eff.type === 'shield') { label = '🛡️'; bg = 'linear-gradient(90deg,#60a5fa,#3b82f6)'; }
          else if (eff.type === 'stun') { label = '😵'; bg = 'linear-gradient(90deg,#f87171,#fb7185)'; }
          else if (eff.type === 'damage_over_time') { label = '🔥'; bg = 'linear-gradient(90deg,#fb923c,#f97316)'; }
          else if (eff.type === 'debuff' || eff.type === 'stat_debuff') { label = '🔻'; bg = 'linear-gradient(90deg,#f43f5e,#ef4444)'; }
          else { label = '✨'; bg = 'linear-gradient(90deg,#a78bfa,#8b5cf6)'; }
          const ttl = eff.expiresAt ? Math.max(0, Math.round((eff.expiresAt - Date.now()) / 1000)) : null
          return (
            <div key={key} title={`${eff.type}${eff.amount ? ` ${eff.amount}` : ''}${ttl !== null ? ` • ${ttl}s` : ''}`} style={{ minWidth: 22, height: 22, borderRadius: 22, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: '#fff', boxShadow: '0 6px 16px rgba(0,0,0,0.35)', background: bg }}>
              <span>{label}</span>
            </div>
          )
        })}
      </div>
      {hasBonusReady && (
        <div
          style={{
            position: 'absolute',
            top: '6px',
            left: '6px',
            background: 'linear-gradient(90deg,#f59e0b,#f97316)',
            color: '#1f1300',
            padding: '2px 6px',
            borderRadius: '999px',
            fontSize: '10px',
            fontWeight: 800,
            boxShadow: '0 4px 10px rgba(249,115,22,0.2)',
            zIndex: 40,
          }}
          title="Bonus attack ready"
        >
          BONUS
        </div>
      )}
      {/* Old inline attack/skill/target visuals removed in favor of projectile VFX */}

      {/* Unit avatar (robust source resolution with fallback) */}
      <img
        src={avatarSrc}
        alt={unit.name}
        style={{ width: '100%', height: '60px', objectFit: 'cover', borderRadius: '0.25rem', marginBottom: '0.25rem' }}
        onError={(e: any) => {
          // Fallback to generic avatar if specific file missing
          if (e?.currentTarget && e.currentTarget.src && !e.currentTarget.src.endsWith('/avatars/default.png')) {
            e.currentTarget.src = '/avatars/default.png'
          }
        }}
      />

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
          className="absolute inset-y-0 left-0"
          style={{
            width: `${displayMaxHp > 0 ? (displayHp / displayMaxHp) * 100 : 0}%`,
            background: `linear-gradient(to right, ${getRarityColor(unit.cost)}, ${getRarityColor(unit.cost)}dd)`,
          }}
        />
      </div>

      <div className="relative h-2 bg-gray-700 rounded-full overflow-hidden border border-gray-600 mt-1">
        <div
          className="absolute inset-y-0 left-0"
          style={{
            width: `${displayMaxMana > 0 ? (displayMana / displayMaxMana) * 100 : 0}%`,
            background: 'linear-gradient(to right, #8b5cf6, #a855f7)',
          }}
        />
      </div>

      {roundStats?.participated && (
        <div
          className="mt-1 grid grid-cols-2 gap-1 rounded border border-slate-600/80 bg-slate-950/60 px-1 py-1 text-[9px] leading-tight"
          title="Średnie statystyki z ostatniej rundy"
        >
          <div>
            <div className="text-orange-300">DPS</div>
            <div className="font-bold text-orange-100">{roundStats.avg_dps.toFixed(1)}</div>
          </div>
          <div>
            <div className="text-red-300">Przyjęte/s</div>
            <div className="font-bold text-red-100">{roundStats.avg_damage_received.toFixed(1)}</div>
          </div>
        </div>
      )}

      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 bg-gray-800 border border-gray-600 text-white text-sm rounded-lg p-4 shadow-xl z-[100] min-w-[300px]">
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
              <div className="mb-1 font-semibold text-amber-300">Pasywka</div>
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
          {roundStats?.participated && (
            <div className="mt-3 grid grid-cols-2 gap-2 border-t border-gray-700 pt-2 text-xs">
              <div className="text-orange-200">Śr. DPS: <strong>{roundStats.avg_dps.toFixed(1)}</strong></div>
              <div className="text-red-200">Przyjęte/s: <strong>{roundStats.avg_damage_received.toFixed(1)}</strong></div>
            </div>
          )}
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
