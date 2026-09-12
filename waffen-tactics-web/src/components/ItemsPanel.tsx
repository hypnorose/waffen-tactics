import { useEffect, useMemo, useRef, useState } from 'react'
import { gameAPI } from '../services/api'
import type { PlayerState } from '../store/gameStore'
import { getRecipePreview, ITEM_ICONS, type Item } from '../data/items'
import ItemTooltip from './ItemTooltip'
import ItemRecipePreviewTooltip from './ItemRecipePreviewTooltip'
import { Panel } from '../ui/primitives'

type Props = {
  playerState: PlayerState
  onUpdate: (state: PlayerState) => void
  onNotification: (message: string, type?: 'error' | 'success' | 'info') => void
  itemCatalog?: Item[]
  onItemDragStart?: (itemId: string) => void
  onItemDragEnd?: () => void
}

export const getItemInstanceKey = (itemId: string, index: number) => `${itemId}-${index}`

interface CombiningPreview {
  first: string
  second: string
  anchor: HTMLElement
}

export default function ItemsPanel({ playerState, onUpdate, onNotification, itemCatalog, onItemDragStart, onItemDragEnd }: Props) {
  const [loadedItems, setLoadedItems] = useState<Item[]>([])
  const [combining, setCombining] = useState<CombiningPreview | null>(null)
  const draggedItem = useRef<{ itemId: string; index: number } | null>(null)
  const items = itemCatalog ?? loadedItems
  const itemById = useMemo(() => new Map(items.map(item => [item.id, item])), [items])
  const owned = playerState.item_inventory || []

  useEffect(() => {
    if (itemCatalog) return
    gameAPI.getItems().then(response => setLoadedItems(response.data)).catch(() => onNotification('Nie udało się pobrać przedmiotów'))
  }, [itemCatalog, onNotification])

  const refresh = async (action: Promise<any>) => {
    try { const response = await action; onUpdate(response.data.state); onNotification(response.data.message, 'success') }
    catch (error: any) { onNotification(error.response?.data?.error || 'Nie udało się wykonać operacji') }
  }

  const previewCombine = (first: string, second: string, anchor: HTMLElement) => {
    setCombining({ first, second, anchor })
  }

  const performCombine = (first: string, second: string, anchor: HTMLElement) => {
    if (!getRecipePreview(items, first, second)) {
      setCombining({ first, second, anchor })
      return
    }
    setCombining(null)
    void refresh(gameAPI.combineItem(first, second))
  }

  const cancelCombine = () => {
    setCombining(null)
  }

  const renderItem = (itemId: string, index: number, equipped = false) => {
    const item = itemById.get(itemId)
    const itemKey = getItemInstanceKey(itemId, index)
    if (!item) return <div
      key={itemKey}
      data-item-state="stale"
      aria-label={`Nieznany przedmiot: ${itemId}`}
      title={`Nieznany przedmiot: ${itemId}`}
      className="relative flex h-12 w-12 items-center justify-center rounded-lg border-2 border-red-400/80 bg-red-950/40 text-lg text-red-200"
    >
      ⚠️
      <span className="sr-only">Nieznany przedmiot: {itemId}</span>
    </div>
    const isCombining = combining && (combining.first === itemId || combining.second === itemId) && !equipped
    return <ItemTooltip key={itemKey} item={item} itemCatalog={items}
      className={`relative flex items-center justify-center w-12 h-12 rounded-lg border-2 text-2xl select-none transition-all ${item.kind === 'combined' ? 'border-amber-300 bg-amber-500/15' : 'border-slate-500 bg-slate-800/80'} ${isCombining ? 'scale-110 ring-2 ring-amber-300 animate-pulse' : 'hover:border-amber-300 hover:-translate-y-0.5'} ${equipped ? 'w-9 h-9 text-lg' : 'cursor-grab active:cursor-grabbing'}`}
      triggerProps={{
        draggable: !equipped,
        tabIndex: equipped ? undefined : 0,
        onDragStart: event => {
          if (!equipped) {
            draggedItem.current = { itemId, index }
            event.dataTransfer.setData('text/item-id', itemId)
            event.dataTransfer.setData('text/item-index', `${index}`)
            onItemDragStart?.(itemId)
          }
        },
        onDragEnd: () => { draggedItem.current = null; cancelCombine(); onItemDragEnd?.() },
        onDragEnter: event => {
          const source = draggedItem.current
          if (source && !(source.itemId === itemId && source.index === index) && !equipped && item.kind === 'base') previewCombine(source.itemId, itemId, event.currentTarget)
        },
        onDragOver: event => event.preventDefault(),
        onDragLeave: event => {
          const nextTarget = event.relatedTarget as Node | null
          if (!nextTarget || !event.currentTarget.contains(nextTarget)) {
            setCombining(current => current?.anchor === event.currentTarget ? null : current)
          }
        },
        onDrop: event => {
          event.preventDefault()
          const source = event.dataTransfer.getData('text/item-id')
          const sourceIndex = Number(event.dataTransfer.getData('text/item-index'))
          if (source && !(source === itemId && sourceIndex === index) && item.kind === 'base') performCombine(source, itemId, event.currentTarget)
        },
        'aria-label': item.name,
      }}>
      {ITEM_ICONS[itemId] || '◆'}
      {!equipped && <span className="absolute -bottom-1 -right-1 rounded-full bg-slate-950 px-1 text-[9px] text-slate-300">{item.kind === 'combined' ? '★' : '×'}</span>}
      {isCombining && <span className="absolute -bottom-5 whitespace-nowrap text-[10px] text-amber-200">łączenie…</span>}
    </ItemTooltip>
  }

  return <Panel variant="raised" className="items-panel border-amber-500/30 p-4">
    <div className="items-panel-header flex items-center justify-between mb-3">
      <div><h2 className="text-lg font-bold">Przedmioty</h2><p className="text-xs text-text/60">Przeciągnij na jednostkę albo na drugi przedmiot, aby połączyć</p></div>
      <span className="text-sm text-text/60">{owned.length} szt.</span>
    </div>
    <div className="items-inventory flex flex-wrap gap-3 min-h-[64px] p-3 rounded-lg bg-slate-950/40 border border-slate-700">
      {owned.map((itemId, index) => renderItem(itemId, index))}
      {!owned.length && <span className="text-sm text-text/50">Brak przedmiotów</span>}
    </div>
    {combining && (() => {
      const first = itemById.get(combining.first)
      const second = itemById.get(combining.second)
      if (!first || !second) return null
      return <ItemRecipePreviewTooltip
        first={first}
        second={second}
        result={getRecipePreview(items, combining.first, combining.second)}
        itemCatalog={items}
        anchor={combining.anchor}
      />
    })()}
  </Panel>
}
