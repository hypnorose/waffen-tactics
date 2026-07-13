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
  return `${attacker} -> ${target}${focus.bonus_attack ? ' [BONUS]' : ''}`
}

export default function CombatSummaryPanel({ summary, synergies }: Props) {
  const topDamage = summary ? getTopDamageDealer(summary) : null
  const activeSynergies = Object.entries(synergies)
    .filter(([, value]) => value.count > 0)
    .sort((a, b) => b[1].tier - a[1].tier)
    .slice(0, 4)

  return (
    <section style={{ marginTop: 12, border: '1px solid #334155', background: 'rgba(15, 23, 42, 0.65)', borderRadius: 8, padding: '10px 12px', color: '#e2e8f0' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <h4 style={{ margin: 0, fontSize: 12, fontWeight: 800, letterSpacing: 0, textTransform: 'uppercase', color: '#cbd5e1' }}>Podsumowanie walki</h4>
        {summary?.bonusAttacks ? (
          <span style={{ background: 'rgba(249, 115, 22, 0.18)', color: '#fdba74', border: '1px solid rgba(249, 115, 22, 0.35)', borderRadius: 999, padding: '2px 8px', fontSize: 11, fontWeight: 800 }}>
            {summary.bonusAttacks} bonus
          </span>
        ) : (
          <span style={{ color: '#94a3b8', fontSize: 11 }}>0 bonus</span>
        )}
      </div>

      <div style={{ display: 'grid', gap: 6, fontSize: 12, lineHeight: 1.35 }}>
        <div><span style={{ color: '#94a3b8' }}>Fokus:</span> {formatFocus(summary?.focus)}</div>
        <div>
          <span style={{ color: '#94a3b8' }}>Top damage:</span>{' '}
          {topDamage ? `${topDamage.unit_name} (${Math.round(topDamage.damage)} dmg)` : 'brak danych'}
        </div>
        <div>
          <span style={{ color: '#94a3b8' }}>Pierwszy upadek:</span>{' '}
          {summary?.firstDeath?.unit_name || summary?.firstDeath?.unit_id || 'brak'}
        </div>
        <div>
          <span style={{ color: '#94a3b8' }}>Ostatnia akcja:</span>{' '}
          {summary?.lastAction?.text || 'brak'}
        </div>
        <div>
          <span style={{ color: '#94a3b8' }}>Wynik:</span>{' '}
          {summary?.roundResult || 'w toku'}
        </div>
      </div>

      <div style={{ marginTop: 10 }}>
        <div style={{ color: '#94a3b8', fontSize: 11, marginBottom: 6, textTransform: 'uppercase', fontWeight: 700 }}>Synergie aktywne</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {activeSynergies.length > 0 ? activeSynergies.map(([name, value]) => (
            <span key={name} style={{ borderRadius: 999, padding: '2px 8px', fontSize: 11, background: 'rgba(59, 130, 246, 0.16)', color: '#bfdbfe', border: '1px solid rgba(59, 130, 246, 0.25)' }}>
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
