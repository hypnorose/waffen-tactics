import { useState, useEffect } from 'react'
import UnitCard from './UnitCard'
import { useGameStore } from '../store/gameStore'
import { gameAPI } from '../services/api'

const getTraitColor = (tier: number) => {
  if (tier === 0) return '#6b7280' // gray - inactive
  const tierColors = ['#6b7280', '#10b981', '#3b82f6', '#a855f7', '#f59e0b']
  if (tier >= tierColors.length - 1) {
    return tierColors[tierColors.length - 1]
  }
  return tierColors[tier] || '#6b7280'
}

interface GameBoardProps {
  playerState: any
  onUpdate: (state: any) => void
}

export default function GameBoard({ playerState, onUpdate }: GameBoardProps) {
  const [loading, setLoading] = useState(false)
  const [traits, setTraits] = useState<any[]>([])
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
      alert('Ławka jest pełna!')
      return
    }

    setLoading(true)
    try {
      const response = await gameAPI.moveToBench(instanceId)
      onUpdate(response.data.state)
    } catch (err: any) {
      alert(err.response?.data?.error || 'Nie można przenieść jednostki')
    } finally {
      setLoading(false)
    }
  }

  // Backend returns synergies as object {traitName: {count, tier}}
  const synergies = playerState.synergies || {}

  return (
    <div className="space-y-4">
      {/* Board Units - Horizontal scroll */}
      {!playerState.board || playerState.board.length === 0 ? (
        <div className="text-center py-8 text-text/60">
          Plansza jest pusta. Przenieś jednostki z ławki!
        </div>
      ) : (
        <div className="flex flex-wrap gap-2 justify-center">
          {playerState.board.map((unitInstance: any) => (
            <div key={unitInstance.instance_id} className="relative">
              <button
                onClick={() => handleMoveToBench(unitInstance.instance_id)}
                disabled={loading || playerState.bench.length >= playerState.max_bench_size}
                className="absolute -top-1 -right-1 z-20 bg-secondary hover:bg-secondary/80 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold disabled:opacity-50 shadow-lg border border-gray-600"
                title="Przenieś na ławkę"
              >
                ↓
              </button>
              <UnitCard unitId={unitInstance.unit_id} starLevel={unitInstance.star_level} showCost={false} detailed={detailedView} baseStats={unitInstance.base_stats} buffedStats={unitInstance.buffed_stats} />
            </div>
          ))}
        </div>
      )}

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
                                    {(() => {
                                      const effect = traitData.effects[idx]
                                      const translateStat = (stat: string) => {
                                        const translations: Record<string, string> = {
                                          'attack_speed': 'Prędkość ataku',
                                          'defense': 'Obrona',
                                          'attack': 'Atak',
                                          'hp': 'HP'
                                        }
                                        return translations[stat] || stat
                                      }
                                      
                                      if (effect.type === 'stat_buff') {
                                        // Handle single stat or multiple stats
                                        if (effect.stat) {
                                          return `+${effect.value}${effect.is_percentage ? '%' : ''} ${translateStat(effect.stat)}`
                                        } else if (effect.stats) {
                                          const statNames = effect.stats.map(translateStat).join(' i ')
                                          return `+${effect.value}${effect.is_percentage ? '%' : ''} ${statNames}`
                                        }
                                      } else if (effect.type === 'on_enemy_death') {
                                        const stats = effect.stats.map(translateStat).join(' i ')
                                        return `+${effect.value} ${stats} za zabójstwo`
                                      } else if (effect.type === 'on_ally_death') {
                                        return `+${effect.value} złota gdy sojusznik umiera`
                                      } else if (effect.type === 'per_round_buff') {
                                        return `+${effect.value}${effect.is_percentage ? '%' : ''} ${translateStat(effect.stat)} co rundę`
                                      } else if (effect.type === 'enemy_debuff') {
                                        return `-${effect.value}${effect.is_percentage ? '%' : ''} ${translateStat(effect.stat)} wrogom`
                                      } else if (effect.type === 'hp_regen_on_kill') {
                                        return `+${effect.value}${effect.is_percentage ? '%' : ''} HP za zabójstwo`
                                      } else if (effect.type === 'per_trait_buff') {
                                        const stats = effect.stats.map(translateStat).join(' i ')
                                        return `+${effect.value}${effect.is_percentage ? '%' : ''} ${stats} za aktywną synergię`
                                      } else if (effect.type === 'mana_regen') {
                                        return `+${effect.value} Many za atak`
                                      } else if (effect.type === 'on_sell_bonus') {
                                        const parts = []
                                        if (effect.gold_per_star > 0) parts.push(`+${effect.gold_per_star} złota za gwiazdkę`)
                                        if (effect.xp > 0) parts.push(`+${effect.xp} XP`)
                                        return parts.join(', ') + ' ze sprzedaży'
                                      } else if (effect.type === 'stat_steal') {
                                        return `Kradnie ${effect.value}${effect.is_percentage ? '%' : ''} ${translateStat(effect.stat)} od wrogów`
                                      } else if (effect.type === 'mana_on_attack') {
                                        return `+${effect.value} Many za atak`
                                      } else if (effect.type === 'lifesteal') {
                                        return `${effect.value}% Kradzież życia`
                                      } else if (effect.type === 'damage_reduction') {
                                        return `${effect.value}% Redukcja obrażeń`
                                      }
                                      return JSON.stringify(effect)
                                    })()}
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
