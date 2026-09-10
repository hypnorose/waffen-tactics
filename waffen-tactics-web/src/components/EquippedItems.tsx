import { ITEM_ICONS, type Item } from '../data/items'

export default function EquippedItems({ itemIds, itemCatalog = [] }: { itemIds?: string[]; itemCatalog?: Item[] }) {
  if (!itemIds?.length) return null

  const itemById = new Map(itemCatalog.map(item => [item.id, item]))

  return <div className="relative z-20 flex min-h-7 items-center justify-center gap-1 px-1 mb-1">
    {itemIds.slice(0, 3).map((itemId, index) => {
      const item = itemById.get(itemId)
      return <div key={`${itemId}-${index}`} className="relative flex h-6 w-6 items-center justify-center rounded border border-amber-300/70 bg-slate-950/90 text-sm shadow" aria-label={item?.name || itemId} title={item?.name || itemId}>
        {ITEM_ICONS[itemId] || '◆'}
      </div>
    })}
  </div>
}
