import { ITEM_PRESENTATION } from '../data/items'

export default function EquippedItems({ itemIds }: { itemIds?: string[] }) {
  if (!itemIds?.length) return null
  return <div className="absolute top-1 right-1 z-20 flex gap-0.5">
    {itemIds.slice(0, 3).map((itemId, index) => {
      const item = ITEM_PRESENTATION[itemId] || { icon: '◆', name: itemId, details: 'Brak opisu przedmiotu.' }
      return <div key={`${itemId}-${index}`} className="group relative flex h-6 w-6 items-center justify-center rounded border border-amber-300/70 bg-slate-950/90 text-sm shadow" title={item.name}>
        {item.icon}
        <div className="pointer-events-none absolute right-0 top-7 hidden w-56 rounded-lg border border-amber-300/60 bg-slate-950 p-2 text-left text-[10px] leading-snug text-slate-100 shadow-2xl group-hover:block">
          <div className="mb-1 text-xs font-bold text-amber-100">{item.icon} {item.name}</div>
          {item.stats && <div className="mb-1 text-emerald-200">{item.stats}</div>}
          <div>{item.details}</div>
        </div>
      </div>
    })}
  </div>
}
