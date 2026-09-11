import { getTraitColor, getTraitDescription, getTraitEffectPresentation } from '../hooks/combatOverlayUtils'
import { SynergiesPanelProps } from './CombatOverlayTypes'
// Note: avatar previews removed from combat overlay to keep overlay lightweight

export default function SynergiesPanel({ synergies, traits, hoveredTrait, setHoveredTrait }: SynergiesPanelProps) {
  return (
    <div>
      {Object.keys(synergies).length > 0 && (
        <div style={{ marginTop: 24 }}>
          <div className="text-xs text-gray-400 mb-2">✨ Aktywne Synergie</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
            {Object.entries(synergies).map(([name, data]) => (
              <div key={name} onMouseEnter={() => setHoveredTrait(name)} onMouseLeave={() => setHoveredTrait(null)} style={{ position: 'relative', padding: '0.25rem 0.5rem', borderRadius: '0.25rem', fontSize: '0.75rem', fontWeight: 'bold', backgroundColor: `${getTraitColor(data.tier)}30`, border: `1.5px solid ${getTraitColor(data.tier)}`, color: getTraitColor(data.tier), cursor: 'pointer', transition: 'all 0.2s' }}>
                {name} [{(data as any).count}] T{(data as any).tier}
                {hoveredTrait === name && (
                  <div style={{ position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)', marginBottom: '0.5rem', padding: '0.5rem', backgroundColor: '#1e293b', border: `2px solid ${getTraitColor((data as any).tier)}`, borderRadius: '0.375rem', zIndex: 100, boxShadow: '0 4px 12px rgba(0,0,0,0.5)', fontSize: '0.7rem', color: '#e2e8f0' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '0.25rem' }}>{name}</div>
                    <div>Tier {(data as any).tier} aktywny ({(data as any).count} jednostek)</div>
                    <div style={{ marginTop: '0.25rem', fontSize: '0.65rem', color: '#cbd5e1' }}>
                      {traits.length > 0 ? (() => {
                        const trait = traits.find(t => t.name === name)
                        if (!trait) return 'Trait nie znaleziony'
                        const tier = Math.max(1, (data as any).tier)
                        return <>
                          <div>{getTraitDescription(trait, tier)}</div>
                          {getTraitEffectPresentation(trait, tier).map((effect, effectIndex) => (
                            <div key={`${name}-${tier}-${effectIndex}`} data-trait-effect-details style={{ marginTop: '0.35rem', padding: '0.35rem', border: '1px solid rgba(148, 163, 184, 0.4)', borderRadius: '0.25rem' }}>
                              <div><span style={{ color: '#94a3b8' }}>Trigger:</span> {effect.trigger}</div>
                              <div><span style={{ color: '#94a3b8' }}>Cel:</span> {effect.target}</div>
                              <div><span style={{ color: '#94a3b8' }}>Czas:</span> {effect.duration}</div>
                              <div><span style={{ color: '#94a3b8' }}>Odświeżanie:</span> {effect.refresh}</div>
                              <div><span style={{ color: '#94a3b8' }}>Stackowanie:</span> {effect.stacking}</div>
                              {effect.conditions.map(condition => <div key={condition}><span style={{ color: '#94a3b8' }}>Warunek:</span> {condition}</div>)}
                            </div>
                          ))}
                        </>
                      })() : 'Ładowanie opisów...'}
                    </div>
                    {/* avatars intentionally omitted in combat overlay */}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
