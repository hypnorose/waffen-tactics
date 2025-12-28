import { useState, useEffect } from 'react'
import UnitCard from './UnitCard'
import { useGameStore } from '../store/gameStore'
import { gameAPI } from '../services/api'
import { getTraitColor, getTraitDescription } from '../hooks/combatOverlayUtils'
import { getAllUnits, getCostBorderColor } from '../data/units'

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
    <div className="space-y-2">
      <div className="flex items-center justify-center gap-2">
        <h3 className={`text-sm font-bold ${lineType === 'front' ? 'text-red-400' : 'text-blue-400'}`}>
          {lineType === 'front' ? '⚔️' : '🏹'} {lineName}
        </h3>
        <span className="text-xs text-text/60">({units.length}/{maxPerLine})</span>
      </div>
      
      <div 
        className={`flex flex-wrap ${detailedView ? 'gap-2' : 'gap-0.5'} justify-center items-center ${detailedView ? 'p-4' : 'p-2'} rounded-lg transition-all duration-200 border-2 mx-auto ${
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
          const data = JSON.parse(e.dataTransfer.getData('text/plain'))
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
                className={`relative ${detailedView ? 'max-w-[14rem]' : 'max-w-[9rem]'}`}
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
                <UnitCard unitId={unitInstance.unit_id} starLevel={unitInstance.star_level} showCost={false} detailed={detailedView} isDragging={isDragging} baseStats={unitInstance.base_stats} buffedStats={unitInstance.buffed_stats} position={unitInstance.position} />
              </div>
            )
          } else {
            // Empty slot placeholder
            return (
              <div key={`empty-${lineType}-${index}`} className={`w-full ${detailedView ? 'max-w-[14rem]' : 'max-w-[9rem]'}`}>
                <div className={`rounded-lg bg-surface/30 ${detailedView ? 'h-64' : 'h-32'} flex items-center justify-center text-text/30 border-2 border-dashed border-gray-600`}>
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
    <div className="space-y-6">
      {/* Construction Notice */}
      <div className="bg-yellow-500/20 border-2 border-yellow-500/50 rounded-lg p-4 text-center">
        <div className="text-xl font-bold text-yellow-600 mb-2">
          🎅 HOŁ HOŁ HOŁ, WESOŁYCH ŚWIĄT BOŻEGO NARODZENIA I BARDZO USZATEGO CWELA 🎅
          {/* 👨‍✈️ MENTOR CWEL MIŁEGO GRANIA 👨‍✈️ */}
        </div>
        {/* <div className="text-sm text-yellow-700">
          Funkcjonalności są w trakcie rozwoju. Przepraszamy za niedogodności!
        </div> */}
      </div>

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
                                {traitData.modular_effects && traitData.modular_effects[idx] && (
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
                      {/* Avatar row for units in this trait (cost-colored border) */}
                      <div style={{ marginTop: 8, display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                        {(() => {
                          try {
                            const all = getAllUnits()
                            const unitsForTrait = all.filter(u => (u.factions || []).includes(traitName) || (u.classes || []).includes(traitName))
                            return unitsForTrait.slice(0, 12).map(u => (
                              <img
                                key={u.id}
                                src={u.avatar || '/avatars/default.png'}
                                title={u.name}
                                alt={u.name}
                                style={{ width: 34, height: 34, borderRadius: '9999px', objectFit: 'cover', border: `2px solid ${getCostBorderColor(u.cost || 1)}` }}
                              />
                            ))
                          } catch (e) {
                            return null
                          }
                        })()}
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
