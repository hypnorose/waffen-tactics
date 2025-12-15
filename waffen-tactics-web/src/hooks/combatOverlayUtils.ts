// Kopia funkcji pomocniczych z CombatOverlay.tsx do refaktoryzacji

const getRarityColor = (cost?: number) => {
  if (!cost) return '#6b7280'
  if (cost === 1) return '#6b7280' // gray
  if (cost === 2) return '#10b981' // green
  if (cost === 3) return '#3b82f6' // blue
  if (cost === 4) return '#a855f7' // purple
  if (cost === 5) return '#f59e0b' // orange/gold
  return '#6b7280'
}

const getRarityGlow = (cost?: number) => {
  const color = getRarityColor(cost)
  return `0 0 10px ${color}40`
}

const getTraitColor = (tier: number) => {
  if (tier === 0) return '#6b7280' // gray - inactive
  const tierColors = ['#6b7280', '#10b981', '#3b82f6', '#a855f7', '#f59e0b']
  if (tier >= tierColors.length - 1) return tierColors[tierColors.length - 1]
  return tierColors[tier] || '#6b7280'
}

const getTraitDescription = (trait: any, tier: number) => {
  if (!trait.threshold_descriptions || tier < 1 || tier > trait.threshold_descriptions.length) {
    return trait.description || 'Brak opisu'
  }
  let template = trait.threshold_descriptions[tier - 1]
  
  // Znajdź wartość z effects
  const effect = trait.effects[tier - 1]
  if (!effect) {
    return template
  }
  
  let params: any = {}
  
  if (effect.actions && effect.actions.length > 0) {
    // Nowy format z actions
    const action = effect.actions[0]
    params.value = action.value || 0
    params.chance = action.chance || 100
    params.duration = action.duration || 0
    params.is_percentage = action.is_percentage || false
  } else {
    // Stary format
    params.value = effect.value || 0
    params.chance = 100
    params.duration = effect.duration || 0
    params.is_percentage = effect.is_percentage || false
  }
  
  // Zastąp placeholdery
  template = template.replace(/<v>/g, params.is_percentage ? `${params.value}%` : params.value.toString())
  template = template.replace(/<c>/g, params.chance.toString())
  template = template.replace(/<d>/g, params.duration.toString())
  
  return template
}

export { getRarityColor, getRarityGlow, getTraitColor, getTraitDescription }
