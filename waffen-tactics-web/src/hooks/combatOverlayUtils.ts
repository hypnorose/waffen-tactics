// Kopia funkcji pomocniczych z CombatOverlay.tsx do refaktoryzacji

const statDisplayNames: { [key: string]: string } = {
  'attack': 'ataku',
  'attack_speed': 'prędkości ataku',
  'defense': 'obrony',
  'health': 'życia',
  'max_health': 'maksymalnego życia',
  'speed': 'szybkości',
  'critical_chance': 'szansy na krytyczne uderzenie',
  'critical_damage': 'obrażeń krytycznych',
  'dodge_chance': 'szansy na unik',
  'damage_reduction': 'redukcji obrażeń',
  'healing_received': 'otrzymywanego leczenia',
  'mana_regen': 'regeneracji many',
  'energy_regen': 'regeneracji energii',
  'lifesteal': 'lifesteala',
  'resource': 'złota',
  'special': 'regeneracji HP',
  'healing': 'leczenia',
  'buff_amplifier': 'mnożnika buffów',
  'reroll_chance': 'szansy na reroll',
  'dynamic_scaling': 'skalowania',
  'targeting_preference': 'priorytetu celu',
  'enemy_debuff': 'osłabienia wrogów',
  // Add more as needed
}

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
  
  return trait.threshold_descriptions[tier - 1] || trait.description || 'Brak opisu'
}

export { getRarityColor, getRarityGlow, getTraitColor, getTraitDescription }
