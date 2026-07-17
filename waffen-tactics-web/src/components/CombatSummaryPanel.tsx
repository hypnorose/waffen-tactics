import type { ReactNode } from 'react'
import { Trophy, Swords, Flame, Skull, Target, Sparkles, Medal } from 'lucide-react'
import { CombatSummary, CombatSummaryFocus } from '../hooks/combat/types'
import { getTopDamageDealer } from '../hooks/combat/combatPresentation'

interface Props {
  summary?: CombatSummary | null
  synergies: Record<string, { count: number; tier: number }>
}

function formatFocus(focus: CombatSummaryFocus | null | undefined): string {
  if (!focus) return 'brak'
  const attacker = focus.attacker_name || focus.attacker_id || 'Unknown'
  const target = focus.target_name || focus.target_id || 'Unknown'
  return `${attacker} -> ${target}`
}

function resultTone(result?: string | null) {
  const value = (result || '').toLowerCase()
  if (value.includes('zw')) {
    return { color: '#86efac', border: 'rgba(34, 197, 94, 0.35)', background: 'rgba(34, 197, 94, 0.14)' }
  }
  if (value.includes('prze')) {
    return { color: '#fca5a5', border: 'rgba(239, 68, 68, 0.35)', background: 'rgba(239, 68, 68, 0.14)' }
  }
  return { color: '#e2e8f0', border: 'rgba(148, 163, 184, 0.2)', background: 'rgba(30, 41, 59, 0.4)' }
}

function StatCard({
  icon,
  label,
  value,
  accent = '#e2e8f0',
  subtitle,
}: {
  icon: ReactNode
  label: string
  value: string
  accent?: string
  subtitle?: string
}) {
  return (
    <div style={{
      border: '1px solid rgba(51, 65, 85, 0.9)',
      background: 'rgba(15, 23, 42, 0.6)',
      borderRadius: 8,
      padding: '8px 10px',
      minWidth: 0,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{
          width: 22,
          height: 22,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 6,
          background: 'rgba(148, 163, 184, 0.12)',
          color: accent,
        }}>
          {icon}
        </span>
        <span style={{ color: '#94a3b8', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0 }}>
          {label}
        </span>
      </div>
      <div style={{ color: accent, fontSize: 14, fontWeight: 800, lineHeight: 1.1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {value}
      </div>
      {subtitle ? (
        <div style={{ color: '#94a3b8', fontSize: 11, marginTop: 3, lineHeight: 1.25, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {subtitle}
        </div>
      ) : null}
    </div>
  )
}

export default function CombatSummaryPanel({ summary, synergies }: Props) {
  const topDamage = summary ? getTopDamageDealer(summary) : null
  const totalDamage = summary
    ? Object.values(summary.totalDamageByUnit).reduce((acc, entry) => acc + (entry.damage || 0), 0)
    : 0
  const topDamageShare = summary && topDamage && totalDamage > 0
    ? Math.round((topDamage.damage || 0) / totalDamage * 100)
    : 0
  const activeSynergies = Object.entries(synergies)
    .filter(([, value]) => value.count > 0)
    .sort((a, b) => b[1].tier - a[1].tier)
    .slice(0, 4)
  const tone = resultTone(summary?.roundResult)

  return (
    <section style={{
      marginTop: 12,
      border: '1px solid rgba(51, 65, 85, 0.95)',
      background: 'rgba(15, 23, 42, 0.72)',
      borderRadius: 8,
      padding: '10px 12px',
      color: '#e2e8f0',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <Trophy size={14} color="#fde68a" />
          <h4 style={{ margin: 0, fontSize: 12, fontWeight: 800, letterSpacing: 0, textTransform: 'uppercase', color: '#cbd5e1' }}>
            Podsumowanie walki
          </h4>
        </div>
        <span style={{
          background: summary?.bonusAttacks ? 'rgba(249, 115, 22, 0.18)' : 'rgba(71, 85, 105, 0.18)',
          color: summary?.bonusAttacks ? '#fdba74' : '#cbd5e1',
          border: '1px solid rgba(249, 115, 22, 0.25)',
          borderRadius: 999,
          padding: '2px 8px',
          fontSize: 11,
          fontWeight: 800,
          whiteSpace: 'nowrap',
        }}>
          {summary?.bonusAttacks ? `${summary.bonusAttacks} bonus attacks` : '0 bonus attacks'}
        </span>
      </div>

      <div style={{
        border: `1px solid ${tone.border}`,
        background: tone.background,
        color: tone.color,
        borderRadius: 8,
        padding: '8px 10px',
        marginBottom: 10,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: 10,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, minWidth: 0, flex: '1 1 220px' }}>
          <Medal size={14} />
          <span style={{ fontSize: 12, fontWeight: 800, textTransform: 'uppercase', letterSpacing: 0, lineHeight: 1.35, overflowWrap: 'anywhere' }}>
            {summary?.roundResult || 'W toku'}
          </span>
        </div>
        <span style={{ fontSize: 11, color: '#cbd5e1', lineHeight: 1.35, flex: '1 1 180px', minWidth: 0, overflowWrap: 'anywhere' }}>
          {summary?.lastAction?.text || 'Brak ostatniej akcji'}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8, marginBottom: 10 }}>
        <StatCard
          icon={<Target size={14} />}
          label="Fokus"
          value={formatFocus(summary?.focus)}
          subtitle={summary?.focus?.bonus_attack ? 'bonus attack ready' : 'normal target selection'}
          accent={summary?.focus?.bonus_attack ? '#fdba74' : '#bfdbfe'}
        />
        <StatCard
          icon={<Swords size={14} />}
          label="Top damage"
          value={topDamage ? `${topDamage.unit_name} - ${Math.round(topDamage.damage || 0)} dmg` : 'brak danych'}
          subtitle={topDamage && totalDamage > 0 ? `${topDamageShare}% z calosci (${Math.round(totalDamage)} dmg)` : undefined}
          accent="#fca5a5"
        />
        <StatCard
          icon={<Skull size={14} />}
          label="Pierwszy upadek"
          value={summary?.firstDeath?.unit_name || summary?.firstDeath?.unit_id || 'brak'}
          subtitle={summary?.firstDeath?.timestamp ? `seq ${summary.firstDeath.seq ?? '-'} | ${summary.firstDeath.timestamp.toFixed(2)}s` : undefined}
          accent="#cbd5e1"
        />
        <StatCard
          icon={<Flame size={14} />}
          label="Tempo"
          value={summary?.bonusAttacks ? `${summary.bonusAttacks}x bonus` : 'brak bonusow'}
          subtitle="bonus attack zastępuje stare skille"
          accent="#fdba74"
        />
      </div>

      <div style={{ marginBottom: 10 }}>
        <div style={{ color: '#94a3b8', fontSize: 11, marginBottom: 6, textTransform: 'uppercase', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Sparkles size={12} />
          Synergie aktywne
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {activeSynergies.length > 0 ? activeSynergies.map(([name, value]) => (
            <span
              key={name}
              style={{
                borderRadius: 999,
                padding: '2px 8px',
                fontSize: 11,
                background: 'rgba(59, 130, 246, 0.16)',
                color: '#bfdbfe',
                border: '1px solid rgba(59, 130, 246, 0.25)',
                whiteSpace: 'nowrap',
              }}
              title={`${name}: ${value.count} units, tier ${value.tier}`}
            >
              {name} {value.count}x t{value.tier}
            </span>
          )) : (
            <span style={{ color: '#64748b', fontSize: 11 }}>brak</span>
          )}
        </div>
      </div>
    </section>
  )
}
