import { ITEM_ICONS, type Item } from '../data/items'

export default function EquippedItems({ itemIds, itemCatalog = [] }: { itemIds?: string[]; itemCatalog?: Item[] }) {
  if (!itemIds?.length) return null

  const itemById = new Map(itemCatalog.map(item => [item.id, item]))

  return <div className="relative z-20 flex min-h-7 items-center justify-center gap-1 px-1 mb-1">
    {itemIds.slice(0, 3).map((itemId, index) => {
      const item = itemById.get(itemId)
      const label = item ? item.name : `Nieznany przedmiot: ${itemId}`
      return <div key={`${itemId}-${index}`} data-item-state={item ? 'known' : 'stale'} className={`relative flex h-6 w-6 items-center justify-center rounded border bg-slate-950/90 text-sm shadow ${item ? 'border-amber-300/70' : 'border-red-400/80 text-red-200'}`} aria-label={label} title={label}>
        {ITEM_ICONS[itemId] || '◆'}
      </div>
    })}
  </div>
}
