import { useState, useEffect } from 'react'
import UnitCard from './UnitCard'
import { useGameStore } from '../store/gameStore'
import { gameAPI } from '../services/api'
import { getTraitColor, getTraitDescription } from '../hooks/combatOverlayUtils'

interface GameBoardProps {
  playerState: any
  onUpdate: (state: any) => void
  onNotification: (message: string, type?: 'error' | 'success' | 'info') => void
}

export default function GameBoard({ playerState, onUpdate, onNotification }: GameBoardProps) {
  const [loading, setLoading] = useState(false)
  const [traits, setTraits] = useState<any[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const { detailedView } = useGameStore()

  useEffect(() => {
    const loadTraits = async () => {
      try {
        const response = await gameAPI.getTraits()
        setTraits(response.data)
      } catch (err) {
        console.error('Failed to load traits:', err)
      }
    }
    loadTraits()
  }, [])

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

  const handleMoveToBoard = async (instanceId: string) => {
    if (playerState.board.length >= playerState.max_board_size) {
      onNotification('Plansza jest pełna!')
      return
    }

    setLoading(true)
    try {
      const response = await gameAPI.moveToBoard(instanceId)
      onUpdate(response.data.state)
    } catch (err: any) {
      onNotification(err.response?.data?.error || 'Nie można przenieść jednostki')
    } finally {
      setLoading(false)
    }
  }

  // Backend returns synergies as object {traitName: {count, tier}}
  const synergies = playerState.synergies || {}

  return (
    <div className="space-y-4">
      {/* Board Units - Grid with placeholders */}
      <div 
        className={`flex flex-wrap gap-2 justify-center p-4 rounded-lg transition-all duration-200 ${isDragOver ? 'ring-2 ring-blue-300 ring-opacity-50' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDragEnd={() => { setIsDragging(false); setIsDragOver(false); }}
        onDrop={async (e) => {
          e.preventDefault()
          setIsDragOver(false)
          const data = JSON.parse(e.dataTransfer.getData('text/plain'))
          if (data.type === 'moveToBoard') {
            // Check if unit is already on board
            if (playerState.board.some((u: any) => u.instance_id === data.instanceId)) {
              return // Already on board
            }
            await handleMoveToBoard(data.instanceId)
          }
        }}
      >
        {Array.from({ length: playerState.max_board_size }).map((_, index) => {
          const unitInstance = playerState.board?.[index]
          
          if (unitInstance) {
            // Occupied slot
            return (
              <div 
                key={unitInstance.instance_id} 
                className="relative"
                draggable
                onDragStart={(e) => {
                  setIsDragging(true)
                  e.dataTransfer.setData('text/plain', JSON.stringify({
                    type: 'moveToBench',
                    instanceId: unitInstance.instance_id
                  }))
                }}
              >
                <button
                  onClick={() => handleMoveToBench(unitInstance.instance_id)}
                  disabled={loading || playerState.bench.length >= playerState.max_bench_size}
                  className="absolute -top-1 -right-1 z-20 bg-secondary hover:bg-secondary/80 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold disabled:opacity-50 shadow-lg border border-gray-600"
                  title="Przenieś na ławkę"
                >
                  ↓
                </button>
                <UnitCard unitId={unitInstance.unit_id} starLevel={unitInstance.star_level} showCost={false} detailed={detailedView} isDragging={isDragging} baseStats={unitInstance.base_stats} buffedStats={unitInstance.buffed_stats} />
              </div>
            )
          } else {
            // Empty slot placeholder
            return (
              <div key={`empty-${index}`} className="w-full max-w-[14rem]">
                <div className="rounded-lg bg-surface/30 h-48 flex items-center justify-center text-text/30 border-2 border-dashed border-gray-600">
                  <span className="text-2xl">∅</span>
                </div>
              </div>
            )
          }
        })}
      </div>

      {/* Synergies - Show active synergies */}
      {Object.keys(synergies).length > 0 && (
        <div className="border-t border-primary/10 pt-4">
          <h3 className="text-sm font-bold mb-3">✨ Synergie</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(synergies)
              .filter(([traitName, data]: [string, any]) => data.count > 0)
              .sort(([, a]: [string, any], [, b]: [string, any]) => b.tier - a.tier)
              .map(([traitName, data]: [string, any]) => {
              const isActive = data.tier > 0
              const color = isActive ? getTraitColor(data.tier) : '#6b7280'
              const opacity = isActive ? 1 : 0.5
              const traitData = traits.find((t: any) => t.name === traitName)
              
              return (
                <div 
                  key={traitName}
                  className="relative group"
                >
                  <div 
                    style={{
                      backgroundColor: `${color}30`,
                      borderColor: color,
                      color: color,
                      opacity: opacity
                    }}
                    className="rounded px-3 py-1 text-xs border-2 font-bold cursor-pointer transition-all hover:opacity-100 hover:scale-105"
                  >
                    {traitName} [{data.count}]{isActive && ` T${data.tier}`}
                  </div>
                  
                  {/* Detailed Tooltip */}
                  {traitData && (
                    <div 
                      style={{
                        backgroundColor: '#1e293b',
                        border: `2px solid ${color}`,
                        color: '#e2e8f0'
                      }}
                      className="hidden group-hover:block absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 p-3 rounded-md z-50 shadow-xl text-xs min-w-[250px] max-w-[350px]"
                    >
                      <div className="font-bold text-sm mb-1" style={{ color: color }}>{traitName}</div>
                      {traitData.description && (
                        <div className="text-gray-300 mb-2 text-xs leading-relaxed">{traitData.description}</div>
                      )}
                      
                      <div className="border-t border-gray-600 pt-2 mt-2">
                        <div className="text-gray-400 text-xs mb-1">Progi aktywacji:</div>
                        {traitData.thresholds.map((threshold: number, idx: number) => {
                          const tierNum = idx + 1
                          const isActive = data.tier >= tierNum
                          const isCurrent = data.tier === tierNum
                          const tierColor = getTraitColor(tierNum)
                          
                          return (
                            <div 
                              key={idx} 
                              className="flex items-start gap-2 mb-1.5 text-xs"
                              style={{ 
                                opacity: isActive ? 1 : 0.6,
                                color: isActive ? tierColor : '#9ca3af'
                              }}
                            >
                              <span className="font-mono font-bold">
                                {isActive ? '✅' : isCurrent ? '⏩' : '⬜'}
                              </span>
                              <div className="flex-1">
                                <div className="font-bold">[{threshold}] Tier {tierNum}</div>
                                {traitData.effects && traitData.effects[idx] && (
                                  <div className="text-xs mt-0.5" style={{ color: isActive ? '#d1d5db' : '#9ca3af' }}>
                                    {getTraitDescription(traitData, tierNum)}
                                  </div>
                                )}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                      
                      <div className="border-t border-gray-600 pt-2 mt-2 text-xs">
                        <span className="text-gray-400">Status: </span>
                        <span style={{ color: isActive ? '#10b981' : '#ef4444', fontWeight: 'bold' }}>
                          {isActive 
                            ? `✓ Tier ${data.tier} Aktywny (${data.count} jednostek)`
                            : `✗ Nieaktywny (${data.count}/${traitData?.thresholds[0] || 0} jednostek)`
                          }
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
