import { useState, useEffect } from 'react'
import { gameAPI } from '../services/api'
import { getCostColor } from '../data/units'

interface TraitsInfoModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function TraitsInfoModal({ isOpen, onClose }: TraitsInfoModalProps) {
  const [traits, setTraits] = useState<any[]>([])
  const [units, setUnits] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      loadData()
    }
  }, [isOpen])

  const loadTraits = async () => {
    setLoading(true)
    try {
      const response = await gameAPI.getTraits()
      setTraits(response.data)
    } catch (err) {
      console.error('Failed to load traits:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadUnits = async () => {
    try {
      const res = await gameAPI.getUnits()
      // API returns array or object with `units` key depending on endpoint
      const data = res.data && (res.data.units || res.data) ? (res.data.units || res.data) : []
      setUnits(data)
    } catch (err) {
      console.error('Failed to load units:', err)
    }
  }

  const loadData = async () => {
    setLoading(true)
    try {
      await Promise.all([loadTraits(), loadUnits()])
    } finally {
      setLoading(false)
    }
  }

  const replacePlaceholders = (description: string, effect: any) => {
    let desc = description

    // Handle modular effects - new structure where effect is array of effects for that tier
    if (Array.isArray(effect) && effect.length > 0) {
      const modularEffect = effect[0] // First effect in the tier's effect array
      if (modularEffect.rewards && modularEffect.rewards.length > 0) {
        const reward = modularEffect.rewards[0] // Assume first reward for now

        // Replace modular effect placeholders
        desc = desc.replace(/<rewards\.stat>/g, reward.stat || '')
        desc = desc.replace(/<rewards\.value>/g, reward.value || '')
        desc = desc.replace(/<rewards\.value_type>/g, reward.value_type || '')
        desc = desc.replace(/<rewards\.resource>/g, reward.resource || '')
        desc = desc.replace(/<rewards\.duration>/g, reward.duration || '')
        desc = desc.replace(/<rewards\.duration_seconds>/g, reward.duration_seconds || '')
        desc = desc.replace(/<rewards\.collect_stat>/g, reward.collect_stat || '')

        // Handle conditions placeholders
        if (modularEffect.conditions) {
          desc = desc.replace(/<conditions\.chance_percent>/g, modularEffect.conditions.chance_percent || '')
          desc = desc.replace(/<conditions\.threshold_percent>/g, modularEffect.conditions.threshold_percent || '')
          desc = desc.replace(/<conditions\.max_triggers>/g, modularEffect.conditions.max_triggers || '')
        }

        // Handle trigger placeholder
        desc = desc.replace(/<trigger>/g, modularEffect.trigger || '')

        // Also handle legacy <v> placeholder for traits that use it with modular effects
        // For traits with multiple rewards of the same value, use that value
        const allValues = modularEffect.rewards.map((r: any) => r.value).filter((v: any) => v !== undefined)
        const uniqueValues = [...new Set(allValues)]
        if (uniqueValues.length === 1) {
          // All rewards have the same value
          const value = uniqueValues[0] as number
          const isPercentage = modularEffect.rewards.some((r: any) => r.value_type === 'percentage_of_max' || r.is_percentage)
          desc = desc.replace(/<v>/g, isPercentage ? `${value}%` : value.toString())
        } else {
          // Different values - use the first one for <v> (fallback)
          const isPercentage = reward.value_type === 'percentage_of_max' || reward.is_percentage
          desc = desc.replace(/<v>/g, isPercentage ? `${reward.value}%` : (reward.value as number)?.toString() || '')
        }

        return desc
      }
    }

    // Fallback to legacy effect handling
    if (effect && effect.actions && effect.actions[0]) {
      const action = effect.actions[0]
      desc = desc.replace(/<v>/g, action.value || '')
      desc = desc.replace(/<d>/g, action.duration || '')
      const chance = action.chance || action.chance_percent
      if (chance && chance !== 100) {
        desc = desc.replace(/<c>/g, chance)
      } else {
        // If chance is 100 or not present, remove <c>% if present
        desc = desc.replace(/<c>% /g, '')
      }
    } else {
      // For effects without actions, like per_second_buff
      desc = desc.replace(/<v>/g, (effect && effect.value) || '')
      desc = desc.replace(/<d>/g, (effect && effect.duration) || '')
      const chance = effect && (effect.chance || effect.chance_percent)
      if (chance && chance !== 100) {
        desc = desc.replace(/<c>/g, chance)
      } else {
        desc = desc.replace(/<c>% /g, '')
      }
    }
    return desc
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-surface border-2 border-primary/30 rounded-lg max-w-4xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-primary/20">
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <span>📚</span> Informacje o Traitach
          </h2>
          <button
            onClick={onClose}
            className="text-text/60 hover:text-text transition-colors text-2xl"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="text-center py-8">Ładowanie...</div>
          ) : (
            <div className="space-y-6">
              {traits.map((trait: any) => (
                <div key={trait.name} className="border border-primary/20 rounded-lg p-4 bg-surface/50">
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="text-xl font-bold text-primary">{trait.name}</h3>
                    <span className={`px-2 py-1 rounded text-xs font-bold ${
                      trait.type === 'faction' ? 'bg-blue-500/20 text-blue-400' :
                      trait.type === 'class' ? 'bg-green-500/20 text-green-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>
                      {trait.type === 'faction' ? 'Frakcja' : trait.type === 'class' ? 'Klasa' : trait.type}
                    </span>
                  </div>
                  
                  <p className="text-text/80 mb-4">{trait.description}</p>
                  
                  {trait.target && (
                    <div className="mb-3">
                      <span className="text-sm font-semibold text-text/60">Cel: </span>
                      <span className={`px-2 py-1 rounded text-xs ${
                        trait.target === 'team' ? 'bg-purple-500/20 text-purple-400' :
                        trait.target === 'trait' ? 'bg-orange-500/20 text-orange-400' :
                        'bg-gray-500/20 text-gray-400'
                      }`}>
                        {trait.target === 'team' ? 'Zespół' : trait.target === 'trait' ? 'Jednostki z traitem' : trait.target}
                      </span>
                    </div>
                  )}
                  
                  <div className="space-y-2">
                    <h4 className="font-semibold text-text/90">Poziomy:</h4>
                    {trait.thresholds.map((threshold: number, index: number) => (
                      <div key={index} className="flex items-center gap-3 text-sm">
                        <span className="font-mono bg-primary/10 px-2 py-1 rounded min-w-[3rem] text-center">
                          {threshold}+
                        </span>
                        <span className="text-text/80">
                          {replacePlaceholders(trait.threshold_descriptions?.[index] || `Poziom ${index + 1}`, trait.effects?.[index])}
                        </span>
                      </div>
                    ))}
                  </div>

                  {/* Units list for this trait */}
                  <div className="mt-3">
                    <h4 className="font-semibold text-text/90 mb-2">Jednostki z tym traitem:</h4>
                    <div className="flex flex-wrap gap-2">
                      {units && units.length > 0 ? (
                        <>
                          {units.filter((u: any) => {
                            const factions = u.factions || []
                            const classes = u.classes || []
                            return factions.includes(trait.name) || classes.includes(trait.name)
                          }).map((u: any) => {
                            const costClass = getCostColor(u.cost || 1).split(' ')[0]
                            return (
                              <div key={u.id} className="flex items-center gap-2 bg-surface/60 px-2 py-1 rounded">
                                <img src={u.avatar || '/avatars/default.png'} alt={u.name} className="w-8 h-8 rounded-full object-cover" />
                                <span className={`text-sm font-medium ${costClass}`}>{u.name}</span>
                              </div>
                            )
                          })}
                        </>
                      ) : (
                        <div className="text-sm text-text/60">Brak jednostek</div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-primary/20 p-4 flex justify-end">
          <button
            onClick={onClose}
            className="btn bg-primary hover:bg-primary/80 px-6 py-2"
          >
            Zamknij
          </button>
        </div>
      </div>
    </div>
  )
}