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

const isPercentageValue = (value: any) => (
  value?.is_percentage === true ||
  value?.value_type === 'percentage' ||
  value?.value_type === 'percentage_of_max' ||
  value?.value_type === 'percentage_of_collected'
)

const formatRewardValue = (reward: any, includeSign = false) => {
  const value = reward?.value
  if (value == null || value === '') return ''
  const numericValue = Number(value)
  const formatted = `${value}${isPercentageValue(reward) ? '%' : ''}`
  return includeSign && Number.isFinite(numericValue) && numericValue > 0 ? `+${formatted}` : formatted
}

const formatReward = (r: any) => {
  const sign = formatRewardValue(r, true)
  const statName = statDisplayNames[r.stat] || r.stat
  return `${sign} ${statName}`
}

const expandTierValues = (description: string, tierIndex: number, tierCount: number) => {
  const sequencePattern = /[+-]?\d+(?:[.,]\d+)?(?:\/[+-]?\d+(?:[.,]\d+)?)+/g
  return description.replace(sequencePattern, sequence => {
    const values = sequence.split('/')
    if (values.length !== tierCount) return sequence
    const selected = values[tierIndex]
    const leadingSign = /^[+-]/.exec(values[0])?.[0] || ''
    return /^[+-]/.test(selected) || !leadingSign ? selected : `${leadingSign}${selected}`
  })
}

const traitTriggerNames: Record<string, string> = {
  passive: 'Efekt pasywny',
  on_attack: 'Przy ataku',
  on_bonus_attack: 'Przy bonusowym ataku',
  on_damage_received: 'Po otrzymaniu obrażeń',
  on_enemy_death: 'Po śmierci wroga',
  on_ally_hp_below: 'Gdy sojusznik spadnie poniżej progu HP',
  per_second: 'Co sekundę',
  on_win: 'Po wygranej rundzie',
  on_loss: 'Po przegranej rundzie',
}

const traitTargetNames: Record<string, string> = {
  owner: 'Właściciel efektu',
  self: 'Ta jednostka',
  team: 'Cały zespół',
  trait: 'Jednostki z tym traitem',
  enemy: 'Wrogowie',
}

const getTraitTierCount = (trait: any) => (
  Array.isArray(trait.thresholds) && trait.thresholds.length > 0
    ? trait.thresholds.length
    : Array.isArray(trait.threshold_descriptions) ? trait.threshold_descriptions.length : 0
)

const getCanonicalTraitDescription = (trait: any, tier: number) => {
  const tierIndex = tier - 1
  const descriptions = Array.isArray(trait.threshold_descriptions) ? trait.threshold_descriptions : []
  const rawDescription = descriptions[tierIndex] || descriptions[0] || trait.description
  if (typeof rawDescription !== 'string' || !rawDescription.trim() || /<[^>]+>/.test(rawDescription)) return undefined
  return expandTierValues(rawDescription, tierIndex, getTraitTierCount(trait))
}

const formatTraitTrigger = (trigger: unknown) => {
  if (typeof trigger !== 'string' || !trigger.trim()) return 'Nie określono'
  return traitTriggerNames[trigger] || trigger.replace(/_/g, ' ')
}

const formatTraitTarget = (target: unknown) => {
  if (typeof target !== 'string' || !target.trim()) return 'Nie określono'
  return traitTargetNames[target] || target.replace(/_/g, ' ')
}

const formatTraitCondition = (key: string, value: unknown) => {
  if (key === 'trigger_once' && value === true) return 'Jednorazowo'
  if (key === 'chance_percent') return `Szansa: ${value}%`
  if (key === 'threshold_percent') return `Próg: ${value}% HP`
  return `${key.replace(/_/g, ' ')}: ${String(value)}`
}

const formatTraitDuration = (effect: any, description?: string) => {
  const candidates = [
    effect?.duration,
    effect?.duration_seconds,
    effect?.duration_s,
    effect?.effect?.duration,
    effect?.effect?.duration_seconds,
    effect?.limit?.duration,
  ]
  const duration = candidates.find(value => typeof value === 'number' && Number.isFinite(value))
  if (duration !== undefined) return `${duration} s`
  if (description && /raz na walkę|raz na zdarzenie|jednorazowo/i.test(description)) return 'Jednorazowo / po wskazanym zdarzeniu'
  if (description && /do końca walki|permanent/i.test(description)) return 'Do końca walki'
  return 'Do review — brak jawnego modelu czasu'
}

const formatTraitRefresh = (description?: string) => {
  if (description && /odśwież/i.test(description)) return 'Po ponownym wyzwoleniu'
  if (description && /powtarza/i.test(description)) return 'Powtarza się po wskazanym zdarzeniu'
  return 'Do review — brak jawnej zasady odświeżania'
}

export interface TraitEffectPresentation {
  trigger: string
  target: string
  duration: string
  refresh: string
  stacking: string
  conditions: string[]
}

export function getTraitEffectPresentation(trait: any, tier: number): TraitEffectPresentation[] {
  const tierIndex = tier - 1
  const tierEffects = Array.isArray(trait?.modular_effects?.[tierIndex]) ? trait.modular_effects[tierIndex] : []
  const description = getCanonicalTraitDescription(trait, tier)

  return tierEffects.map((effect: any) => {
    const conditions = effect?.conditions && typeof effect.conditions === 'object'
      ? Object.entries(effect.conditions)
        .filter(([, value]) => value !== undefined && value !== null && value !== false && value !== '')
        .map(([key, value]) => formatTraitCondition(key, value))
      : []
    const stacking = effect?.limit?.stacking
    return {
      trigger: formatTraitTrigger(effect?.trigger),
      target: formatTraitTarget(effect?.target || trait?.target),
      duration: formatTraitDuration(effect, description),
      refresh: formatTraitRefresh(description),
      stacking: stacking === 'none' ? 'Bez stackowania' : stacking ? String(stacking) : 'Do review — brak jawnej zasady stackowania',
      conditions,
    }
  })
}

const getTraitDescription = (trait: any, tier: number) => {
  const hasThresholds = Array.isArray(trait.threshold_descriptions)
  const tierCount = getTraitTierCount(trait)
  if (!hasThresholds || tier < 1 || tier > tierCount) {
    return trait.description || 'Brak opisu'
  }

  const template = getCanonicalTraitDescription(trait, tier) || trait.threshold_descriptions[tier - 1]

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
  const hasReadableReward = rewards.some((reward: any) => (
    typeof reward?.stat === 'string' || ['healing', 'damage', 'shield'].includes(reward?.type)
  ))

  // Special Set 2 effects carry their player-facing meaning in the canonical
  // description while rewards.value is only an internal runtime parameter.
  if (!hasReadableReward && template) return template

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
    out = out.replace(/<rewards.value>/g, formatRewardValue(rewards[0], true))
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
