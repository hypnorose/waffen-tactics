import { useState } from 'react'
import UnitCard from './UnitCard'
import { useGameStore } from '../store/gameStore'
import { gameAPI } from '../services/api'

interface BenchProps {
  playerState: any
  onUpdate: (state: any) => void
  onNotification: (message: string, type?: 'error' | 'success' | 'info') => void
}

export default function Bench({ playerState, onUpdate, onNotification }: BenchProps) {
  const [loading, setLoading] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const { detailedView } = useGameStore()

  const handleMoveToBoard = async (instanceId: string) => {
    const maxPerLine = Math.ceil(playerState.max_board_size * 0.75)
    const frontCount = playerState.board.filter((u: any) => u.position === 'front').length

    if (frontCount >= maxPerLine) {
      onNotification(`Linia frontowa jest pełna! (max ${maxPerLine})`)
      return
    }

    if (playerState.board.length >= playerState.max_board_size) {
      onNotification('Plansza jest pełna!')
      return
    }

    setLoading(true)
    try {
      const response = await gameAPI.moveToBoard(instanceId, 'front')
      onUpdate(response.data.state)
    } catch (err: any) {
      onNotification(err.response?.data?.error || 'Nie można przenieść jednostki')
    } finally {
      setLoading(false)
    }
  }

  const handleMoveToBench = async (instanceId: string) => {
    if (playerState.bench.length >= playerState.max_bench_size) {
      onNotification('Ławka jest pełna!')
      return
    }

    setLoading(true)
    try {
      const response = await gameAPI.moveToBench(instanceId)
      onUpdate(response.data.state)
    } catch (err: any) {
      onNotification(err.response?.data?.error || 'Nie można przenieść jednostki')
    } finally {
      setLoading(false)
    }
  }

  const handleSell = async (instanceId: string) => {
    setLoading(true)
    try {
      const response = await gameAPI.sellUnit(instanceId)
      onUpdate(response.data.state)
      
      if (response.data.message) {
        onNotification(response.data.message, 'success')
      }
    } catch (err: any) {
      onNotification(err.response?.data?.error || 'Nie można sprzedać jednostki')
    } finally {
      setLoading(false)
    }
  }

  const handleBuyUnit = async (unitId: string) => {
    setLoading(true)
    try {
      const response = await gameAPI.buyUnit(unitId)
      onUpdate(response.data.state)

      // Show success message if present
      if (response.data.message) {
        onNotification(response.data.message, 'success')
      }
    } catch (err: any) {
      onNotification(err.response?.data?.error || 'Nie można kupić jednostki')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div 
        className={`flex flex-wrap ${detailedView ? 'gap-2' : 'gap-0.5'} justify-center items-center ${detailedView ? 'p-4' : 'p-2'} rounded-lg transition-all duration-200 mx-auto ${isDragOver ? 'ring-2 ring-green-300 ring-opacity-50' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDragEnd={() => { setIsDragging(false); setIsDragOver(false); }}
        onDrop={async (e) => {
          e.preventDefault()
          setIsDragOver(false)
          const data = JSON.parse(e.dataTransfer.getData('text/plain'))
          if (data.type === 'unitAction') {
            if (data.action === 'moveToBoard') {
              // Check if unit is already on bench
              if (playerState.bench.some((u: any) => u.instance_id === data.instanceId)) {
                return // Already on bench
              }
              await handleMoveToBench(data.instanceId)
            } else if (data.action === 'buy') {
              await handleBuyUnit(data.unitId)
            }
          }
        }}
      >
        {playerState.bench.map((unitInstance: any) => (
          <div 
            key={unitInstance.instance_id} 
            className={`flex-shrink-0 relative ${detailedView ? '' : 'max-w-[9rem]'}`}
            draggable
            onDragStart={(e) => {
              setIsDragging(true)
              e.dataTransfer.setData('text/plain', JSON.stringify({
                type: 'unitAction',
                action: 'sell',
                instanceId: unitInstance.instance_id
              }))
            }}
          >
            <div className="absolute -top-1 -right-1 z-20 flex gap-1">
              <button
                onClick={() => handleMoveToBoard(unitInstance.instance_id)}
                disabled={loading || playerState.board.length >= playerState.max_board_size}
                className="bg-primary hover:bg-primary/80 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold disabled:opacity-50 shadow-lg border border-primary-dark"
                title="Przenieś na planszę"
              >
                ↑
              </button>
              <button
                onClick={() => handleSell(unitInstance.instance_id)}
                disabled={loading}
                className="bg-red-500 hover:bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold disabled:opacity-50 shadow-lg border border-red-700"
                title="Sprzedaj jednostkę"
              >
                💰
              </button>
            </div>
            <UnitCard unitId={unitInstance.unit_id} starLevel={unitInstance.star_level} showCost={false} detailed={detailedView} isDragging={isDragging} baseStats={unitInstance.base_stats} buffedStats={unitInstance.buffed_stats} />
          </div>
        ))}
        {/* Show one placeholder if bench is not full */}
        {playerState.bench.length < playerState.max_bench_size && (
          <div className={`flex-shrink-0 ${detailedView ? '' : 'max-w-[9rem]'}`}>
            <div className={`rounded-lg bg-surface/30 ${detailedView ? 'w-56 h-64' : 'w-36 h-32'} flex items-center justify-center text-text/30 border-2 border-dashed border-gray-600`}>
              <span className="text-2xl">∅</span>
            </div>
          </div>
        )}
      </div>
      {(!playerState.bench || playerState.bench.length === 0) && (
        <div className="text-center py-8 text-text/60">
          Ławka jest pusta. Kup jednostki w sklepie!
        </div>
      )}
    </div>
  )
}
