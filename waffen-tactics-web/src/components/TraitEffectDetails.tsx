import type { TraitEffectPresentation } from '../hooks/combatOverlayUtils'

interface Props {
  effect: TraitEffectPresentation
  compact?: boolean
}

export default function TraitEffectDetails({ effect, compact = false }: Props) {
  const value = effect.values.length > 0
    ? effect.values.join(' · ')
    : 'Do review — brak jawnej wartości'

  return (
    <div
      data-trait-effect-details
      className={`${compact ? 'p-1.5 text-[11px]' : 'p-2 text-xs'} rounded border border-gray-600/70 bg-black/10 leading-snug`}
    >
      <div><span className="text-gray-400">Trigger:</span> {effect.trigger}</div>
      <div><span className="text-gray-400">Cel:</span> {effect.target}</div>
      <div data-trait-effect-values><span className="text-gray-400">Wartość:</span> {value}</div>
      <div><span className="text-gray-400">Lifecycle:</span> {effect.lifecycle}</div>
      <div><span className="text-gray-400">Aktywacja:</span> {effect.activation}</div>
      <div><span className="text-gray-400">Czas:</span> {effect.duration}</div>
      <div><span className="text-gray-400">Odświeżanie:</span> {effect.refresh}</div>
      <div><span className="text-gray-400">Ponowienie:</span> {effect.retrigger}</div>
      <div><span className="text-gray-400">Stackowanie:</span> {effect.stacking}</div>
      <div><span className="text-gray-400">Wygaśnięcie:</span> {effect.expiresWhen}</div>
      {effect.conditions.map(condition => (
        <div key={condition}><span className="text-gray-400">Warunek:</span> {condition}</div>
      ))}
    </div>
  )
}
