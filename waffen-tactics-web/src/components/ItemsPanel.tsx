import { useEffect, useMemo, useRef, useState } from 'react'
import { gameAPI } from '../services/api'
import type { PlayerState } from '../store/gameStore'

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
  const [hoveredItem, setHoveredItem] = useState<string | null>(null)
  const [combining, setCombining] = useState<[string, string] | null>(null)
  const combineTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const draggedItem = useRef<string | null>(null)
  const itemById = useMemo(() => new Map(items.map(item => [item.id, item])), [items])
  const owned = playerState.item_inventory || []

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

  const statLabels: Record<string, string> = {
    attack: 'Obrażenia', defense: 'Obrona', hp: 'Maks. HP', attack_speed: 'Szybkość ataku',
    mana_regen: 'Regeneracja many', max_mana: 'Maks. mana', hp_regen_per_sec: 'Regeneracja HP/s'
  }

  const formatStat = (stat: string, value: number) => {
    const amount = value > 0 ? `+${value}` : `${value}`
    if (stat === 'attack_speed') return `${amount} ataku/s`
    if (stat === 'hp_regen_per_sec') return `${amount} HP/s`
    return `${amount} ${statLabels[stat] || stat}`
  }

  const renderTooltip = (item: Item) => <div className="pointer-events-none absolute bottom-[calc(100%+10px)] left-1/2 z-50 w-64 -translate-x-1/2 rounded-lg border border-amber-300/60 bg-slate-950 px-3 py-2 text-left text-xs shadow-2xl">
    <div className="mb-1 flex items-center gap-2 text-sm font-bold text-amber-100"><span className="text-lg">{ICONS[item.id] || '◆'}</span>{item.name}</div>
    <div className="mb-2 text-[10px] uppercase tracking-wide text-slate-400">{item.kind === 'combined' ? 'Przedmiot połączony' : 'Przedmiot bazowy'}</div>
    <div className="space-y-0.5 text-emerald-200">{Object.entries(item.stats).map(([stat, value]) => <div key={stat}>{formatStat(stat, value)}</div>)}</div>
    {item.description && <div className="mt-2 border-t border-slate-700 pt-2 leading-snug text-slate-200">{item.description}</div>}
    {item.components && <div className="mt-2 border-t border-slate-700 pt-2 text-[11px] text-indigo-200">Składniki: {item.components.map(component => itemById.get(component)?.name || component).join(' + ')}</div>}
    <div className="mt-2 text-[10px] text-slate-500">Przeciągnij na kartę jednostki lub drugi przedmiot</div>
  </div>

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
      onMouseEnter={() => setHoveredItem(itemId)}
      onMouseLeave={() => { setHoveredItem(null); cancelCombine() }}
      title={`${item.name}${item.description ? ` — ${item.description}` : ''}`}
      className={`relative flex items-center justify-center w-12 h-12 rounded-lg border-2 text-2xl select-none transition-all ${item.kind === 'combined' ? 'border-amber-300 bg-amber-500/15' : 'border-slate-500 bg-slate-800/80'} ${isCombining ? 'scale-110 ring-2 ring-amber-300 animate-pulse' : 'hover:border-amber-300 hover:-translate-y-0.5'} ${equipped ? 'w-9 h-9 text-lg' : 'cursor-grab active:cursor-grabbing'}`}>
      {ICONS[itemId] || '◆'}
      {!equipped && <span className="absolute -bottom-1 -right-1 rounded-full bg-slate-950 px-1 text-[9px] text-slate-300">{item.kind === 'combined' ? '★' : '×'}</span>}
      {isCombining && <span className="absolute -bottom-5 whitespace-nowrap text-[10px] text-amber-200">łączenie…</span>}
      {hoveredItem === itemId && !equipped && renderTooltip(item)}
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
    {combining && <div className="mt-3 text-center text-xs text-amber-200">Przytrzymaj przedmiot na drugim, aby utworzyć {itemById.get(items.find(item => item.components?.includes(combining[0]) && item.components?.includes(combining[1]))?.id || '')?.name || 'nowy przedmiot'}.</div>}
  </section>
}
