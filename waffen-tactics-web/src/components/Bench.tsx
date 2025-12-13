import { useState } from 'react'
import UnitCard from './UnitCard'
import { useGameStore } from '../store/gameStore'
import { gameAPI } from '../services/api'

interface BenchProps {
  playerState: any
  onUpdate: (state: any) => void
}

export default function Bench({ playerState, onUpdate }: BenchProps) {
  const [loading, setLoading] = useState(false)
  const { detailedView } = useGameStore()

  const handleMoveToBoard = async (instanceId: string) => {
    if (playerState.board.length >= playerState.max_board_size) {
      alert('Plansza jest pełna!')
      return
    }

    setLoading(true)
    try {
      const response = await gameAPI.moveToBoard(instanceId)
      onUpdate(response.data.state)
    } catch (err: any) {
      alert(err.response?.data?.error || 'Nie można przenieść jednostki')
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
        console.log('✅', response.data.message)
      }
    } catch (err: any) {
      alert(err.response?.data?.error || 'Nie można sprzedać jednostki')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      {!playerState.bench || playerState.bench.length === 0 ? (
        <div className="text-center py-8 text-text/60">
          Ławka jest pusta. Kup jednostki w sklepie!
        </div>
      ) : (
        <div className="flex flex-wrap gap-2 justify-center">
          {playerState.bench.map((unitInstance: any) => (
            <div key={unitInstance.instance_id} className="flex-shrink-0 relative">
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
              <UnitCard unitId={unitInstance.unit_id} starLevel={unitInstance.star_level} showCost={false} detailed={detailedView} buffedStats={unitInstance.buffed_stats} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
