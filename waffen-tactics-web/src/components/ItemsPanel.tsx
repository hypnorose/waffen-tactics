import { useEffect, useMemo, useRef, useState } from 'react'
import { gameAPI } from '../services/api'
import type { PlayerState, UnitInstance } from '../store/gameStore'

type Item = { id: string; name: string; kind: 'base' | 'combined'; components?: string[]; stats: Record<string, number>; description?: string }
type Props = { playerState: PlayerState; onUpdate: (state: PlayerState) => void; onNotification: (message: string, type?: 'error' | 'success' | 'info') => void }

const ICONS: Record<string, string> = {
  spices: '🌶️', orangeade: '🥤', coat: '🧥', safe: '🔐', socks: '🧦', notebook: '💌',
  sugar_rush: '✨', seasoned_armor: '🛡️', contraband: '🌶️🔐', hot_feet: '🔥', recipe_for_love: '💖',
  warm_drink: '☕', emergency_reserve: '🧰', bubbly_steps: '🫧', sweet_memory: '🍬', fortified_vault: '🏰',
  woolen_stride: '🏃', love_warmth: '❤️‍🔥', quick_draw: '⚡', secure_heart: '💗', love_on_the_move: '💞'
}

export default function ItemsPanel({ playerState, onUpdate, onNotification }: Props) {
  const [items, setItems] = useState<Item[]>([])
  const [combining, setCombining] = useState<[string, string] | null>(null)
  const combineTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const draggedItem = useRef<string | null>(null)
  const itemById = useMemo(() => new Map(items.map(item => [item.id, item])), [items])
  const owned = playerState.item_inventory || []
  const units = [...playerState.board, ...playerState.bench]

  useEffect(() => {
    gameAPI.getItems().then(response => setItems(response.data)).catch(() => onNotification('Nie udało się pobrać przedmiotów'))
    return () => { if (combineTimer.current) clearTimeout(combineTimer.current) }
  }, [onNotification])

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

  const renderItem = (itemId: string, index: number, equipped = false) => {
    const item = itemById.get(itemId)
    if (!item) return null
    const isCombining = combining?.includes(itemId) && !equipped
    return <div key={`${itemId}-${index}`} draggable={!equipped}
      onDragStart={event => { if (!equipped) { draggedItem.current = itemId; event.dataTransfer.setData('text/item-id', itemId) } }}
      onDragEnd={() => { draggedItem.current = null; cancelCombine() }}
      onDragEnter={event => {
        const source = draggedItem.current
        if (source && source !== itemId && !equipped && item.kind === 'base') finishCombine(source, itemId)
      }}
      onDragOver={event => event.preventDefault()}
      onDrop={event => {
        event.preventDefault()
        const source = event.dataTransfer.getData('text/item-id')
        if (source && source !== itemId && item.kind === 'base') finishCombine(source, itemId)
      }}
      onMouseLeave={cancelCombine}
      title={`${item.name}${item.description ? ` — ${item.description}` : ''}`}
      className={`relative flex items-center justify-center w-12 h-12 rounded-lg border-2 text-2xl select-none transition-all ${item.kind === 'combined' ? 'border-amber-300 bg-amber-500/15' : 'border-slate-500 bg-slate-800/80'} ${isCombining ? 'scale-110 ring-2 ring-amber-300 animate-pulse' : 'hover:border-amber-300 hover:-translate-y-0.5'} ${equipped ? 'w-9 h-9 text-lg' : 'cursor-grab active:cursor-grabbing'}`}>
      {ICONS[itemId] || '◆'}
      {!equipped && <span className="absolute -bottom-1 -right-1 rounded-full bg-slate-950 px-1 text-[9px] text-slate-300">{item.kind === 'combined' ? '★' : '×'}</span>}
      {isCombining && <span className="absolute -bottom-5 whitespace-nowrap text-[10px] text-amber-200">łączenie…</span>}
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
    <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
      {units.map((unit: UnitInstance) => <div key={unit.instance_id}
        onDragOver={event => event.preventDefault()}
        onDrop={event => { event.preventDefault(); const itemId = event.dataTransfer.getData('text/item-id'); if (itemId) refresh(gameAPI.equipItem(unit.instance_id, itemId)) }}
        className="flex items-center gap-2 min-h-[58px] rounded-lg border border-slate-700 bg-slate-900/60 px-2 py-1 hover:border-emerald-400/70">
        <div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold">{unit.unit_id}</div><div className="text-[10px] text-text/50">upuść tutaj · {(unit.items || []).length}/3</div></div>
        <div className="flex gap-1">{(unit.items || []).map((itemId, index) => renderItem(itemId, index, true))}</div>
      </div>)}
    </div>
    {combining && <div className="mt-3 text-center text-xs text-amber-200">Przytrzymaj przedmiot na drugim, aby utworzyć {itemById.get(items.find(item => item.components?.includes(combining[0]) && item.components?.includes(combining[1]))?.id || '')?.name || 'nowy przedmiot'}.</div>}
  </section>
}
