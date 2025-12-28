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

const formatReward = (r: any) => {
  const val = r.value
  const isPct = r.value_type === 'percentage' || r.is_percentage === true
  const formattedVal = isPct ? `${val}%` : `${val}`
  const sign = typeof val === 'number' && val > 0 ? `+${formattedVal}` : `${formattedVal}`
  const statName = statDisplayNames[r.stat] || r.stat
  return `${sign} ${statName}`
}

const getTraitDescription = (trait: any, tier: number) => {
  const hasThresholds = Array.isArray(trait.threshold_descriptions)
  if (!hasThresholds || tier < 1 || tier > trait.threshold_descriptions.length) {
    return trait.description || 'Brak opisu'
  }

  const template = trait.threshold_descriptions[tier - 1]

  // modular_effects is an array of tiers -> arrays of effects
  const tierEffects = trait.modular_effects && trait.modular_effects[tier - 1]
  if (!Array.isArray(tierEffects) || tierEffects.length === 0) {
    return template || trait.description || 'Brak opisu'
  }

  // find the first effect that contains rewards
  const effectWithRewards = tierEffects.find((e: any) => Array.isArray(e.rewards) && e.rewards.length > 0)
  if (!effectWithRewards) return template || trait.description || 'Brak opisu'

  const rewards = effectWithRewards.rewards
  const rewardParts = rewards.map((r: any) => {
    if (r.type === 'stat_buff') return formatReward(r)
    // fallback for unknown reward types
    if (r.value != null) return (r.value > 0 ? `+${r.value}` : `${r.value}`) + (r.stat ? ` ${r.stat}` : '')
    return ''
  }).filter(Boolean)

  const rewardsStr = rewardParts.join(' ')

  // If template contains condition/trigger placeholders prefer the concrete rewards string
  if (template.includes('<trigger') || template.includes('<conditions')) {
    return rewardsStr || template
  }

  // If template explicitly references rewards placeholders (or any angle-bracket placeholders), prefer the concrete rewards string
  if ((template.includes('<rewards.value>') || template.includes('<rewards.stat>') || (template.includes('<') && template.includes('>'))) && rewardsStr) {
    return rewardsStr
  }

  // If template contains explicit rewards placeholders, replace them
  let out = template

  // replace <v> with first reward raw value (no percent sign)
  if (out.includes('<v>') && rewards.length > 0) {
    out = out.replace(/<v>/g, `${rewards[0].value}`)
  }

  // replace <rewards.value> and <rewards.stat>
  if (out.includes('<rewards.value>') && rewards.length > 0) {
    const val = rewards[0].value
    const isPct = rewards[0].value_type === 'percentage' || rewards[0].is_percentage === true
    const formattedVal = isPct ? `${val}%` : `${val}`
    out = out.replace(/<rewards.value>/g, (val > 0 ? `+${formattedVal}` : `${formattedVal}`))
  }
  if (out.includes('<rewards.stat>') && rewards.length > 0) {
    out = out.replace(/<rewards.stat>/g, statDisplayNames[rewards[0].stat] || rewards[0].stat)
  }

  // also translate any raw stat words present in the template
  Object.keys(statDisplayNames).forEach((k) => {
    const re = new RegExp(`\\b${k}\\b`, 'g')
    if (re.test(out)) out = out.replace(re, statDisplayNames[k])
  })

  // If template looks generic (no placeholders) but we have a concrete rewards string, prefer it
  const hasPlaceholders = /<|>/.test(template)
  if (!hasPlaceholders && rewardsStr) return rewardsStr

  return out || trait.description || 'Brak opisu'
}

export { getRarityColor, getRarityGlow, getTraitColor, getTraitDescription }
