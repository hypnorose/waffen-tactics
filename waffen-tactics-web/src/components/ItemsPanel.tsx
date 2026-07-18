import { useEffect, useMemo, useState } from 'react'
import { gameAPI } from '../services/api'
import type { PlayerState } from '../store/gameStore'

type Item = { id: string; name: string; kind: 'base' | 'combined'; components?: string[]; stats: Record<string, number>; description?: string }
type Props = { playerState: PlayerState; onUpdate: (state: PlayerState) => void; onNotification: (message: string, type?: 'error' | 'success' | 'info') => void }

export default function ItemsPanel({ playerState, onUpdate, onNotification }: Props) {
  const [items, setItems] = useState<Item[]>([])
  const [selectedUnit, setSelectedUnit] = useState(playerState.board[0]?.instance_id || playerState.bench[0]?.instance_id || '')
  const itemById = useMemo(() => new Map(items.map(item => [item.id, item])), [items])
  const owned = playerState.item_inventory || []
  const allUnits = [...playerState.board, ...playerState.bench]

  useEffect(() => { gameAPI.getItems().then(response => setItems(response.data)).catch(() => onNotification('Nie udało się pobrać przedmiotów')) }, [])

  const refresh = async (action: Promise<any>) => {
    try { const response = await action; onUpdate(response.data.state); onNotification(response.data.message, 'success') }
    catch (error: any) { onNotification(error.response?.data?.error || 'Nie udało się wykonać operacji') }
  }

  const combine = async (first: string, second: string) => refresh(gameAPI.combineItem(first, second))
  const equip = async (itemId: string) => refresh(gameAPI.equipItem(selectedUnit, itemId))

  return <div className="card border border-amber-500/30">
    <div className="flex items-center justify-between gap-3 mb-3">
      <h2 className="text-lg font-bold">Przedmioty <span className="text-sm text-text/60">{owned.length} w ekwipunku</span></h2>
      <select value={selectedUnit} onChange={event => setSelectedUnit(event.target.value)} className="bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm">
        {allUnits.map(unit => <option key={unit.instance_id} value={unit.instance_id}>{unit.unit_id} ({(unit.items || []).length}/3)</option>)}
      </select>
    </div>
    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
      {owned.map((itemId, index) => { const item = itemById.get(itemId); return <button key={`${itemId}-${index}`} onClick={() => equip(itemId)} disabled={!selectedUnit} title={item?.description || ''} className="text-left border border-slate-600 hover:border-amber-400 rounded p-2 bg-slate-900/60">
        <div className="font-semibold text-sm">{item?.name || itemId}</div><div className="text-[11px] text-text/60">Załóż</div>
      </button> })}
    </div>
    <div className="mt-3 text-xs text-text/60">Połącz dwa różne przedmioty bazowe:</div>
    <div className="flex flex-wrap gap-2 mt-1">{owned.filter((id, index, list) => list.indexOf(id) === index).map(first => owned.filter(second => second !== first && second !== undefined).map(second => {
      const result = itemById.get(items.find(item => item.components?.includes(first) && item.components?.includes(second))?.id || '')
      return result ? <button key={`${first}-${second}`} onClick={() => combine(first, second)} className="text-xs px-2 py-1 rounded border border-indigo-400/50 hover:bg-indigo-500/20">{itemById.get(first)?.name} + {itemById.get(second)?.name}</button> : null
    }))}</div>
  </div>
}
