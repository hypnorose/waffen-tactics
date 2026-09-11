import { useState, useEffect } from 'react'
import UnitCard from './UnitCard'
import { useGameStore } from '../store/gameStore'
import { gameAPI } from '../services/api'
import type { CombatUnitRoundStats } from '../hooks/combat/types'
import { getUnitItemPreview, type Item } from '../data/items'
import TraitSynergyTooltip from './TraitSynergyTooltip'

interface GameBoardProps {
  playerState: any
  onUpdate: (state: any) => void
  onNotification: (message: string, type?: 'error' | 'success' | 'info') => void
  roundStatsByUnit?: Record<string, CombatUnitRoundStats>
  onEquipItem?: (instanceId: string, itemId: string) => void
  itemCatalog?: Item[]
  draggedItemId?: string | null
}

export default function GameBoard({ playerState, onUpdate, onNotification, roundStatsByUnit, onEquipItem, itemCatalog = [], draggedItemId = null }: GameBoardProps) {
  const [loading, setLoading] = useState(false)
  const [traits, setTraits] = useState<any[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const [previewTargetId, setPreviewTargetId] = useState<string | null>(null)
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

  useEffect(() => {
    if (!draggedItemId) setPreviewTargetId(null)
  }, [draggedItemId])

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

  const handleMoveToBoard = async (instanceId: string, position: 'front' | 'back' = 'front') => {
    const maxPerLine = Math.ceil(playerState.max_board_size * 0.75)
    const frontCount = playerState.board.filter((u: any) => u.position === 'front').length
    const backCount = playerState.board.filter((u: any) => u.position === 'back').length

    if (position === 'front' && frontCount >= maxPerLine) {
      onNotification(`Linia frontowa jest pełna! (max ${maxPerLine})`)
      return
    }
    if (position === 'back' && backCount >= maxPerLine) {
      onNotification(`Linia tylna jest pełna! (max ${maxPerLine})`)
      return
    }

    if (playerState.board.length >= playerState.max_board_size) {
      onNotification('Plansza jest pełna!')
      return
    }

    setLoading(true)
    try {
      const response = await gameAPI.moveToBoard(instanceId, position)
      onUpdate(response.data.state)
    } catch (err: any) {
      onNotification(err.response?.data?.error || 'Nie można przenieść jednostki')
    } finally {
      setLoading(false)
    }
  }

  const handleSwitchLine = async (instanceId: string, currentPosition: 'front' | 'back') => {
    const newPosition = currentPosition === 'front' ? 'back' : 'front'

    setLoading(true)
    try {
      const response = await gameAPI.switchLine(instanceId, newPosition)
      onUpdate(response.data.state)
    } catch (err: any) {
      onNotification(err.response?.data?.error || 'Nie można zmienić linii')
    } finally {
      setLoading(false)
    }
  }

  // Backend returns synergies as object {traitName: {count, tier}}
  const synergies = playerState.synergies || {}

  // Separate units by position
  const frontLineUnits = playerState.board?.filter((unit: any) => unit.position === 'front') || []
  const backLineUnits = playerState.board?.filter((unit: any) => unit.position === 'back') || []

  const renderUnitGrid = (units: any[], lineName: string, lineType: 'front' | 'back') => {
    const maxPerLine = Math.ceil(playerState.max_board_size * 0.75)
    return (
    <div className="board-line space-y-2">
      <div className="flex items-center justify-center gap-2">
        <h3 className={`text-sm font-bold ${lineType === 'front' ? 'text-red-400' : 'text-blue-400'}`}>
          {lineType === 'front' ? '⚔️' : '🏹'} {lineName}
        </h3>
        <span className="text-xs text-text/60">({units.length}/{maxPerLine})</span>
      </div>
      
      <div 
        className={`board-line-grid flex flex-wrap ${detailedView ? 'gap-2' : 'gap-0.5'} justify-center items-center ${detailedView ? 'p-4' : 'p-2'} rounded-lg transition-all duration-200 border-2 mx-auto ${
          lineType === 'front' 
            ? 'border-red-500/30 bg-red-500/5' 
            : 'border-blue-500/30 bg-blue-500/5'
        } ${isDragOver ? 'ring-2 ring-blue-300 ring-opacity-50' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDragEnd={() => { setIsDragging(false); setIsDragOver(false); }}
        onDrop={async (e) => {
          e.preventDefault()
          setIsDragOver(false)
          const rawData = e.dataTransfer.getData('text/plain')
          if (!rawData) return
          let data: any
          try { data = JSON.parse(rawData) } catch { return }
          if (data.type === 'unitAction') {
            if (data.action === 'sell') {
              // If dragging from bench to board, move to board instead of sell
              await handleMoveToBoard(data.instanceId, lineType)
            } else if (data.action === 'moveToBoard') {
              // Check if unit is already on board
              if (playerState.board.some((u: any) => u.instance_id === data.instanceId)) {
                // Unit is already on board, check if it's in a different line
                const existingUnit = playerState.board.find((u: any) => u.instance_id === data.instanceId)
                if (existingUnit.position !== lineType) {
                  await handleSwitchLine(data.instanceId, existingUnit.position)
                }
                return
              }
              await handleMoveToBoard(data.instanceId, lineType)
            } else if (data.action === 'buy') {
              await handleBuyUnit(data.unitId)
            }
          }
        }}
      >
        {Array.from({ length: maxPerLine }).map((_, index) => {
          const unitInstance = units[index]
          
          if (unitInstance) {
            // Occupied slot
            return (
              <div 
                key={unitInstance.instance_id} 
                className={`board-unit-card-slot ${detailedView ? 'board-unit-card-slot-detailed' : ''} relative`}
                onDragEnter={event => {
                  if (draggedItemId || event.dataTransfer.types.includes('text/item-id')) {
                    event.preventDefault()
                    setPreviewTargetId(unitInstance.instance_id)
                  }
                }}
                onDragOver={event => {
                  if (draggedItemId || event.dataTransfer.types.includes('text/item-id')) {
                    event.preventDefault()
                    setPreviewTargetId(unitInstance.instance_id)
                  }
                }}
                onDragLeave={event => {
                  const nextTarget = event.relatedTarget as Node | null
                  if (!nextTarget || !event.currentTarget.contains(nextTarget)) setPreviewTargetId(null)
                }}
                onDrop={event => {
                  event.preventDefault()
                  event.stopPropagation()
                  setPreviewTargetId(null)
                  const itemId = event.dataTransfer.getData('text/item-id')
                  if (itemId) onEquipItem?.(unitInstance.instance_id, itemId)
                }}
                onDragEnd={() => setPreviewTargetId(null)}
                draggable
                onDragStart={(e) => {
                  setIsDragging(true)
                  e.dataTransfer.setData('text/plain', JSON.stringify({
                    type: 'unitAction',
                    action: 'moveToBoard',
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
                <button
                  onClick={() => handleSell(unitInstance.instance_id)}
                  disabled={loading}
                  className="absolute -bottom-1 -right-1 z-20 bg-red-500 hover:bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold disabled:opacity-50 shadow-lg border border-red-700"
                  title="Sprzedaj jednostkę"
                >
                  💰
                </button>
                <button
                  onClick={() => handleSwitchLine(unitInstance.instance_id, unitInstance.position)}
                  disabled={loading}
                  className={`absolute -top-1 -left-1 z-20 rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold disabled:opacity-50 shadow-lg border border-gray-600 ${
                    lineType === 'front' 
                      ? 'bg-blue-500 hover:bg-blue-600 text-white' 
                      : 'bg-red-500 hover:bg-red-600 text-white'
                  }`}
                  title={`Przenieś do ${lineType === 'front' ? 'tylnej' : 'frontowej'} linii`}
                >
                  {lineType === 'front' ? '⬇' : '⬆'}
                </button>
                <UnitCard unitId={unitInstance.unit_id} starLevel={unitInstance.star_level} showCost={false} detailed={detailedView} boardLayout isDragging={isDragging} items={unitInstance.items} itemCatalog={itemCatalog} baseStats={unitInstance.base_stats} buffedStats={unitInstance.buffed_stats} position={unitInstance.position} lastRoundStats={roundStatsByUnit?.[unitInstance.instance_id]} itemPreview={previewTargetId === unitInstance.instance_id && draggedItemId ? getUnitItemPreview(itemCatalog, unitInstance.items || [], draggedItemId) ?? undefined : undefined} />
              </div>
            )
          } else {
            // Empty slot placeholder
            return (
              <div key={`empty-${lineType}-${index}`} className={`board-unit-card-slot ${detailedView ? 'board-unit-card-slot-detailed' : ''}`}>
                <div className={`board-unit-card-empty ${detailedView ? 'board-unit-card-empty-detailed' : ''} rounded-lg bg-surface/30 flex items-center justify-center text-text/30 border-2 border-dashed border-gray-600`} aria-hidden="true">
                  <span className="text-2xl">∅</span>
                </div>
              </div>
            )
          }
        })}
      </div>
    </div>
  )
}
  return (
    <div className="game-board space-y-6">
      {/* Construction Notice */}
      {/* Front Line */}
      {renderUnitGrid(frontLineUnits, 'Linia Frontowa', 'front')}
      
      {/* Back Line */}
      {renderUnitGrid(backLineUnits, 'Linia Tylna', 'back')}

      {/* Synergies - Show active synergies */}
      {Object.keys(synergies).length > 0 && (
        <div className="border-t border-primary/10 pt-4">
          <h3 className="text-sm font-bold mb-3">✨ Synergie</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(synergies)
              .filter(([traitName, data]: [string, any]) => data.count > 0)
              .sort(([, a]: [string, any], [, b]: [string, any]) => b.count - a.count)
              .map(([traitName, data]: [string, any]) => {
              const traitData = traits.find((t: any) => t.name === traitName)

              return (
                <TraitSynergyTooltip
                  key={traitName}
                  traitName={traitName}
                  data={data}
                  traitData={traitData}
                />
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
