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
  const template = trait.threshold_descriptions[tier - 1]
  if (!template.includes('<v>')) {
    return template
  }
  // Znajdź wartość z effects
  const effect = trait.effects[tier - 1]
  if (!effect || !effect.value) {
    return template.replace('<v>', '0')
  }
  const value = effect.value
  const isPercentage = effect.is_percentage
  const formattedValue = isPercentage ? `${value}%` : value.toString()
  return template.replace('<v>', formattedValue)
}

export { getRarityColor, getRarityGlow, getTraitColor, getTraitDescription }
