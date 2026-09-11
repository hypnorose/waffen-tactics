import { formatItemStat, formatItemTrigger, getItemMechanicDescription, ITEM_ICONS, type Item } from '../data/items'

export default function ItemTooltipContent({ item, itemCatalog, showHint = true }: { item: Item; itemCatalog: Item[]; showHint?: boolean }) {
  const itemById = new Map(itemCatalog.map(candidate => [candidate.id, candidate]))
  const mechanicDescription = getItemMechanicDescription(item)

  return (
    <div data-item-tooltip-content>
      <div className="mb-1 flex items-center gap-2 text-sm font-bold text-amber-100">
        <span className="text-lg">{ITEM_ICONS[item.id] || '◆'}</span>
        {item.name}
      </div>
      <div className="mb-2 text-[10px] uppercase tracking-wide text-slate-400">
        {item.kind === 'combined' ? 'Przedmiot połączony' : 'Przedmiot bazowy'}
      </div>
      <div className="space-y-0.5 text-emerald-200">
        {Object.entries(item.stats).map(([stat, value]) => <div key={stat}>{formatItemStat(stat, value)}</div>)}
      </div>
      {mechanicDescription && <div className="mt-2 border-t border-slate-700 pt-2 leading-snug text-slate-200">{mechanicDescription}</div>}
      {item.effect && <div className="mt-2 border-t border-slate-700 pt-2 text-[11px] text-cyan-200">
        <div>Aktywacja: {formatItemTrigger(item.effect.trigger)}</div>
        {item.effect.duration !== null && <div>Czas działania: {item.effect.duration} s</div>}
        {item.effect.stacking.max_stacks > 1 && <div>Stacki: maks. {item.effect.stacking.max_stacks}</div>}
      </div>}
      {item.components && <div className="mt-2 border-t border-slate-700 pt-2 text-[11px] text-indigo-200">
        Składniki: {item.components.map(component => itemById.get(component)?.name || component).join(' + ')}
      </div>}
      {showHint && <div className="mt-2 text-[10px] text-slate-500">Przeciągnij na kartę jednostki lub drugi przedmiot</div>}
    </div>
  )
}
