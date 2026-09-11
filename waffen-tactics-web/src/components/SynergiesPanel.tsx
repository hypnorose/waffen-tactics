import { SynergiesPanelProps } from './CombatOverlayTypes'
import TraitSynergyTooltip from './TraitSynergyTooltip'

export default function SynergiesPanel({ synergies, traits }: SynergiesPanelProps) {
  return (
    <div>
      {Object.keys(synergies).length > 0 && (
        <div style={{ marginTop: 24 }}>
          <div className="text-xs text-gray-400 mb-2">✨ Aktywne Synergie</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
            {Object.entries(synergies)
              .filter(([, data]) => data.count > 0)
              .map(([name, data]) => {
                const traitData = traits.find(trait => trait.name === name)
                if (!traitData) {
                  return <div key={name} role="status" className="text-xs text-slate-400">{name} — Trait nie znaleziony</div>
                }
                return <TraitSynergyTooltip key={name} traitName={name} data={data} traitData={traitData} />
              })}
          </div>
        </div>
      )}
    </div>
  )
}
