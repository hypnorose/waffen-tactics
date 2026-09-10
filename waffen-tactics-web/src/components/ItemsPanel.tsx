import { useEffect, useMemo, useRef, useState } from 'react'
import { gameAPI } from '../services/api'
import type { PlayerState } from '../store/gameStore'
import { formatItemStat, formatItemTrigger, getRecipePreview, ITEM_ICONS, type Item } from '../data/items'

type Props = { playerState: PlayerState; onUpdate: (state: PlayerState) => void; onNotification: (message: string, type?: 'error' | 'success' | 'info') => void; itemCatalog?: Item[] }

export const getItemInstanceKey = (itemId: string, index: number) => `${itemId}-${index}`

export default function ItemsPanel({ playerState, onUpdate, onNotification, itemCatalog }: Props) {
  const [loadedItems, setLoadedItems] = useState<Item[]>([])
  const [hoveredItemKey, setHoveredItemKey] = useState<string | null>(null)
  const [combining, setCombining] = useState<[string, string] | null>(null)
  const combineTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const draggedItem = useRef<{ itemId: string; index: number } | null>(null)
  const items = itemCatalog ?? loadedItems
  const itemById = useMemo(() => new Map(items.map(item => [item.id, item])), [items])
  const owned = playerState.item_inventory || []

  useEffect(() => {
    if (itemCatalog) return
    gameAPI.getItems().then(response => setLoadedItems(response.data)).catch(() => onNotification('Nie udało się pobrać przedmiotów'))
    return () => { if (combineTimer.current) clearTimeout(combineTimer.current) }
  }, [itemCatalog, onNotification])

  const refresh = async (action: Promise<any>) => {
    try { const response = await action; onUpdate(response.data.state); onNotification(response.data.message, 'success') }
    catch (error: any) { onNotification(error.response?.data?.error || 'Nie udało się wykonać operacji') }
  }

  const finishCombine = (first: string, second: string) => {
    if (combineTimer.current) clearTimeout(combineTimer.current)
    setCombining([first, second])
    combineTimer.current = setTimeout(() => {
      setCombining(null)
      refresh(gameAPI.combineItem(first, second))
    }, 850)
  }

  const cancelCombine = () => {
    if (combineTimer.current) clearTimeout(combineTimer.current)
    combineTimer.current = null
    setCombining(null)
  }

  const renderTooltip = (item: Item) => <div className="pointer-events-none absolute bottom-[calc(100%+10px)] left-1/2 z-50 w-64 -translate-x-1/2 rounded-lg border border-amber-300/60 bg-slate-950 px-3 py-2 text-left text-xs shadow-2xl">
    <div className="mb-1 flex items-center gap-2 text-sm font-bold text-amber-100"><span className="text-lg">{ITEM_ICONS[item.id] || '◆'}</span>{item.name}</div>
    <div className="mb-2 text-[10px] uppercase tracking-wide text-slate-400">{item.kind === 'combined' ? 'Przedmiot połączony' : 'Przedmiot bazowy'}</div>
    <div className="space-y-0.5 text-emerald-200">{Object.entries(item.stats).map(([stat, value]) => <div key={stat}>{formatItemStat(stat, value)}</div>)}</div>
    {item.description && <div className="mt-2 border-t border-slate-700 pt-2 leading-snug text-slate-200">{item.description}</div>}
    {item.effect && <div className="mt-2 border-t border-slate-700 pt-2 text-[11px] text-cyan-200">
      <div>Aktywacja: {formatItemTrigger(item.effect.trigger)}</div>
      {item.effect.duration !== null && <div>Czas działania: {item.effect.duration} s</div>}
      {item.effect.stacking.max_stacks > 1 && <div>Stacki: maks. {item.effect.stacking.max_stacks}</div>}
    </div>}
    {item.components && <div className="mt-2 border-t border-slate-700 pt-2 text-[11px] text-indigo-200">Składniki: {item.components.map(component => itemById.get(component)?.name || component).join(' + ')}</div>}
    <div className="mt-2 text-[10px] text-slate-500">Przeciągnij na kartę jednostki lub drugi przedmiot</div>
  </div>

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
    const isCombining = combining?.includes(itemId) && !equipped
    return <div key={itemKey} draggable={!equipped}
      onDragStart={event => { if (!equipped) { draggedItem.current = { itemId, index }; event.dataTransfer.setData('text/item-id', itemId); event.dataTransfer.setData('text/item-index', `${index}`) } }}
      onDragEnd={() => { draggedItem.current = null; cancelCombine() }}
      onDragEnter={event => {
        const source = draggedItem.current
        if (source && !(source.itemId === itemId && source.index === index) && !equipped && item.kind === 'base') finishCombine(source.itemId, itemId)
      }}
      onDragOver={event => event.preventDefault()}
      onDrop={event => {
        event.preventDefault()
        const source = event.dataTransfer.getData('text/item-id')
        const sourceIndex = Number(event.dataTransfer.getData('text/item-index'))
        if (source && !(source === itemId && sourceIndex === index) && item.kind === 'base') finishCombine(source, itemId)
      }}
      onMouseEnter={() => setHoveredItemKey(itemKey)}
      onMouseLeave={() => { setHoveredItemKey(null); cancelCombine() }}
      aria-label={`${item.name}${item.description ? ` — ${item.description}` : ''}`}
      className={`relative flex items-center justify-center w-12 h-12 rounded-lg border-2 text-2xl select-none transition-all ${item.kind === 'combined' ? 'border-amber-300 bg-amber-500/15' : 'border-slate-500 bg-slate-800/80'} ${isCombining ? 'scale-110 ring-2 ring-amber-300 animate-pulse' : 'hover:border-amber-300 hover:-translate-y-0.5'} ${equipped ? 'w-9 h-9 text-lg' : 'cursor-grab active:cursor-grabbing'}`}>
      {ITEM_ICONS[itemId] || '◆'}
      {!equipped && <span className="absolute -bottom-1 -right-1 rounded-full bg-slate-950 px-1 text-[9px] text-slate-300">{item.kind === 'combined' ? '★' : '×'}</span>}
      {isCombining && <span className="absolute -bottom-5 whitespace-nowrap text-[10px] text-amber-200">łączenie…</span>}
      {hoveredItemKey === itemKey && !equipped && renderTooltip(item)}
    </div>
  }

  return <section className="card border border-amber-500/30">
    <div className="flex items-center justify-between mb-3">
      <div><h2 className="text-lg font-bold">Przedmioty</h2><p className="text-xs text-text/60">Przeciągnij na jednostkę albo na drugi przedmiot, aby połączyć</p></div>
      <span className="text-sm text-text/60">{owned.length} szt.</span>
    </div>
    <div className="flex flex-wrap gap-3 min-h-[64px] p-3 rounded-lg bg-slate-950/40 border border-slate-700">
      {owned.map((itemId, index) => renderItem(itemId, index))}
      {!owned.length && <span className="text-sm text-text/50">Brak przedmiotów</span>}
    </div>
    {combining && (() => {
      const preview = getRecipePreview(items, combining[0], combining[1])
      return <div className="mt-3 text-center text-xs text-amber-200">
        {preview
          ? <>Przytrzymaj przedmiot na drugim, aby utworzyć {preview.name}.</>
          : <>Brak receptury dla tej pary przedmiotów.</>}
      </div>
    })()}
  </section>
}
