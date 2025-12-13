import { useState } from 'react'
import UnitCard from './UnitCard'
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

  // Backend returns ALL synergies (active and inactive) already sorted
  const allSynergies = playerState.synergies || []

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
              <UnitCard unitId={unitInstance.unit_id} starLevel={unitInstance.star_level} showCost={false} />
            </div>
          ))}
        </div>
      )}

      {/* Synergies - Show ALL traits (active and inactive) */}
      {allSynergies.length > 0 && (
        <div className="border-t border-primary/10 pt-4">
          <h3 className="text-sm font-bold mb-3">✨ Synergie</h3>
          <div className="flex flex-wrap gap-2">
            {allSynergies.map((data: any) => {
              const traitName = data.name
              const color = data.active ? getTraitColor(data.tier) : '#6b7280'
              const opacity = data.active ? 1 : 0.5
              
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
                    {traitName} [{data.count}]{data.active && ` T${data.tier}`}
                  </div>
                  
                  {/* Detailed Tooltip */}
                  <div 
                    style={{
                      backgroundColor: '#1e293b',
                      border: `2px solid ${color}`,
                      color: '#e2e8f0'
                    }}
                    className="hidden group-hover:block absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 p-3 rounded-md z-50 shadow-xl text-xs min-w-[250px] max-w-[350px]"
                  >
                    <div className="font-bold text-sm mb-1" style={{ color: color }}>{traitName}</div>
                    {data.description && (
                      <div className="text-gray-300 mb-2 text-xs leading-relaxed">{data.description}</div>
                    )}
                    
                    <div className="border-t border-gray-600 pt-2 mt-2">
                      <div className="text-gray-400 text-xs mb-1">Progi aktywacji:</div>
                      {data.thresholds.map((threshold: number, idx: number) => {
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
                              {data.effects && data.effects[idx] && (
                                <div className="text-xs mt-0.5" style={{ color: isActive ? '#d1d5db' : '#9ca3af' }}>
                                  {(() => {
                                    const effect = data.effects[idx]
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
                      <span style={{ color: data.active ? '#10b981' : '#ef4444', fontWeight: 'bold' }}>
                        {data.active 
                          ? `✓ Tier ${data.tier} Aktywny (${data.count} jednostek)`
                          : `✗ Nieaktywny (${data.count}/${data.thresholds[0]} jednostek)`
                        }
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
