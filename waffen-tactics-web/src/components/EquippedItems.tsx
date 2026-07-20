import { ITEM_PRESENTATION } from '../data/items'

export default function EquippedItems({ itemIds }: { itemIds?: string[] }) {
  if (!itemIds?.length) return null

  return <div className="relative z-20 flex min-h-7 items-center justify-center gap-1 px-1 mb-1">
    {itemIds.slice(0, 3).map((itemId, index) => {
      const item = ITEM_PRESENTATION[itemId] || { icon: '◆' }
      return <div key={`${itemId}-${index}`} className="relative flex h-6 w-6 items-center justify-center rounded border border-amber-300/70 bg-slate-950/90 text-sm shadow" aria-label={itemId}>
        {item.icon}
      </div>
    })}
  </div>
}
