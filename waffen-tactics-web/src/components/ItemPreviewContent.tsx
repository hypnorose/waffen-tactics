import { ITEM_ICONS, type Item, type ItemUnitPreview } from '../data/items'
import ItemTooltipContent from './ItemTooltipContent'

const itemLabel = (item: Item) => `${ITEM_ICONS[item.id] || '◆'} ${item.name}`

export function ItemRecipePreviewContent({ first, second, result, itemCatalog }: {
  first: Item
  second: Item
  result?: Item
  itemCatalog: Item[]
}) {
  return (
    <div data-item-preview-content>
      <div className="mb-2 text-sm font-bold text-amber-100">Podgląd receptury</div>
      <div className="mb-2 rounded border border-slate-700 bg-slate-900/70 p-2 text-xs text-slate-200">
        <div>{itemLabel(first)} + {itemLabel(second)}</div>
        <div className="mt-1 text-amber-300">→ {result ? itemLabel(result) : 'brak legalnej kombinacji'}</div>
      </div>
      {result
        ? <ItemTooltipContent item={result} itemCatalog={itemCatalog} showHint={false} />
        : <div className="text-xs leading-snug text-red-200">Ta para nie ma receptury w zatwierdzonym katalogu WFT-139. Stan inventory pozostaje bez zmian.</div>}
    </div>
  )
}

export function ItemUnitPreviewContent({ preview, itemCatalog }: {
  preview: ItemUnitPreview
  itemCatalog: Item[]
}) {
  const itemById = new Map(itemCatalog.map(item => [item.id, item]))

  return (
    <div data-item-preview-content>
      <div className="mb-2 text-sm font-bold text-amber-100">Podgląd wyposażenia</div>
      <div className="mb-2 rounded border border-slate-700 bg-slate-900/70 p-2 text-xs text-slate-200">
        <div className="text-slate-400">{preview.mode === 'auto-combine' ? 'Auto-combine' : preview.mode === 'equip' ? 'Założenie' : 'Brak legalnej operacji'}</div>
        <div className="mt-1 text-amber-200">{ITEM_ICONS[preview.incomingItem.id] || '◆'} {preview.incomingItem.name}</div>
        {preview.mode === 'auto-combine' && (
          <div className="mt-1 text-cyan-200">
            {preview.replacedItemId && itemById.get(preview.replacedItemId)?.name} → {preview.resultingItem.name}
            {preview.slotIndex !== undefined && ` · slot ${preview.slotIndex + 1}`}
          </div>
        )}
      </div>

      {preview.legal
        ? <ItemTooltipContent item={preview.resultingItem} itemCatalog={itemCatalog} showHint={false} />
        : <div className="mb-2 text-xs leading-snug text-red-200">{preview.reason}</div>}

      <div className="border-t border-slate-700 pt-2 text-[11px] text-slate-200">
        <div className="mb-1 font-semibold text-slate-400">Wyposażenie po operacji</div>
        <div className="space-y-0.5">
          {preview.nextItemIds.map((itemId, index) => <div key={`${itemId}-${index}`}>{index + 1}. {itemById.get(itemId)?.name || itemId}</div>)}
          {!preview.nextItemIds.length && <div className="text-slate-500">brak</div>}
        </div>
      </div>

    </div>
  )
}
