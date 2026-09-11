import { ITEM_ICONS, type Item } from '../data/items'
import ItemTooltip from './ItemTooltip'

export default function EquippedItems({ itemIds, itemCatalog = [] }: { itemIds?: string[]; itemCatalog?: Item[] }) {
  if (!itemIds?.length) return null

  const itemById = new Map(itemCatalog.map(item => [item.id, item]))

  return <div className="relative z-20 flex min-h-7 items-center justify-center gap-1 px-1 mb-1">
    {itemIds.slice(0, 3).map((itemId, index) => {
      const item = itemById.get(itemId)
      const label = item ? item.name : `Nieznany przedmiot: ${itemId}`
      if (!item) return <div key={`${itemId}-${index}`} data-item-state="stale" className="relative flex h-6 w-6 items-center justify-center rounded border border-red-400/80 bg-slate-950/90 text-sm text-red-200 shadow" aria-label={label} title={label}>
        {ITEM_ICONS[itemId] || '◆'}
      </div>
      return <ItemTooltip key={`${itemId}-${index}`} item={item} itemCatalog={itemCatalog}
        className="relative flex h-6 w-6 items-center justify-center rounded border border-amber-300/70 bg-slate-950/90 text-sm shadow"
        triggerProps={{ 'data-item-state': 'known', 'aria-label': label, title: label }}>
        {ITEM_ICONS[itemId] || '◆'}
      </ItemTooltip>
    })}
  </div>
}
