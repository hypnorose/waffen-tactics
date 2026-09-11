export interface ItemEffect {
  family: string
  description: string
  trigger: string
  target: string
  scope: string
  order: string
  duration: number | null
  stacking: { mode: string; max_stacks: number }
  cap: number | null
  reset_between_fights: boolean
  rng: { mode: string; seed: string }
  replay: { mode: string; event_types: string[] }
  parameters?: Record<string, unknown>
}

export interface Item {
  id: string
  name: string
  kind: 'base' | 'combined'
  components: string[]
  stats: Record<string, number>
  effect: ItemEffect | null
  description?: string
  content_version: string
}

export interface ItemUnitPreview {
  legal: boolean
  incomingItem: Item
  resultingItem: Item
  nextItemIds: string[]
  mode: 'equip' | 'auto-combine' | 'blocked'
  replacedItemId?: string
  slotIndex?: number
  statChanges: Record<string, number>
  reason?: string
}

// Icons are presentation-only. Names, stats, components, and descriptions
// always come from the backend WFT-139 catalog.
export const ITEM_ICONS: Record<string, string> = {
  spices: '🌶️',
  orangeade: '🥤',
  coat: '🧥',
  safe: '🔐',
  socks: '🧦',
  notebook: '💌',
  etf_przyprawowy: '✨',
  helena_o_smaku_kurkumy: '🌶️🥤',
  plaszcz_ze_100_bawelny: '🌶️🧥',
  skrytka_na_oregano: '🌶️🔐',
  ponetne_stopki: '🌶️🧦',
  pikante_slowka: '🌶️💌',
  mandarynkowy_sodastream: '🥤✨',
  bluza_z_bytom: '🥤🧥',
  kolekcja_syropow: '🥤🔐',
  kremik_owocowy: '🥤🧦',
  telewizor_4k_50_cali: '🥤💌',
  plaszcz_200_welny: '🧥✨',
  forteca_z_ksiazek: '🧥🔐',
  fartuszek_femboya: '🧥🧦',
  full_plate_cum_armor: '🧥💌',
  skruszony_zab: '🔐✨',
  zestaw_do_makijazu_po_edycie: '🔐🧦',
  fap_folder: '🔐💌',
  stopki_rozmiar_44: '🧦✨',
  idealny_traf: '🧦💌',
  encyklopedia_seksu: '💌✨',
}

const ITEM_STAT_LABELS: Record<string, string> = {
  attack: 'Obrażenia',
  defense: 'Obrona',
  hp: 'Maks. HP',
  attack_speed: 'Szybkość ataku',
  mana_regen: 'Regeneracja many',
  max_mana: 'Maks. mana',
  hp_regen_per_sec: 'Regeneracja HP/s',
  lifesteal_percent: 'Life steal (%)',
}

export const formatItemStat = (stat: string, value: number) => {
  const amount = value > 0 ? `+${value}` : `${value}`
  if (stat === 'attack_speed') return `${amount} ataku/s`
  if (stat === 'hp_regen_per_sec') return `${amount} HP/s`
  return `${amount} ${ITEM_STAT_LABELS[stat] || stat}`
}

const ITEM_STAT_DESCRIPTION_PHRASES: Record<string, string[]> = {
  attack: ['ataku', 'obrażeń', 'ATK'],
  defense: ['obrony', 'DEF'],
  hp: ['HP'],
  attack_speed: ['szybkości ataku', 'attack speed', 'ataku/s'],
  mana_regen: ['regeneracji many', 'many/s', 'mana/s', 'mana regen'],
  max_mana: ['maks\\.?\\s*many', 'max\\.?\\s*mana'],
  hp_regen_per_sec: ['HP regeneracji/s', 'regeneracji HP/s', 'HP/s', 'health regen/s'],
  lifesteal_percent: ['life\\s*steal', 'lifesteal'],
}

const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

const itemStatNumberVariants = (value: number) => {
  const raw = String(value)
  const trimmed = raw.includes('.') ? raw.replace(/0+$/, '').replace(/\.$/, '') : raw
  const variants = new Set([raw, raw.replace('.', ','), trimmed, trimmed.replace('.', ',')])
  if (!Number.isInteger(value)) {
    const fixed = value.toFixed(2)
    variants.add(fixed)
    variants.add(fixed.replace('.', ','))
  }
  return [...variants].sort((first, second) => second.length - first.length)
}

const itemStatDescriptionPattern = (stat: string, value: number) => {
  const phrases = ITEM_STAT_DESCRIPTION_PHRASES[stat]
  if (!phrases) return null
  const numberPattern = itemStatNumberVariants(value).map(escapeRegExp).join('|')
  const phrasePattern = phrases.join('|')
  return new RegExp(
    `^\\s*[+-]?\\s*(?:${numberPattern})${stat === 'lifesteal_percent' ? '\\s*%?' : ''}\\s+(?:${phrasePattern})(?=\\s*(?:[,\\.]|$))`,
    'i',
  )
}

const hasLeadingItemStatDescription = (description: string, stats: Record<string, number>) => (
  Object.entries(stats).some(([stat, value]) => itemStatDescriptionPattern(stat, value)?.test(description) ?? false)
)

/**
 * Keep only the mechanic-specific part of the canonical item description.
 * Numeric stat rows are generated from `item.stats`, so matching leading
 * clauses are removed without touching different proc values such as a
 * per-attack +1 attack bonus.
 */
export const getItemMechanicDescription = (item: Item) => {
  const description = item.description?.trim() || item.effect?.description?.trim()
  if (!description) return undefined

  let remaining = description
  if (/^(?:daje|zapewnia|dodaje|posiada|otrzymuje)\s+/i.test(remaining)) {
    const withoutLeadIn = remaining.replace(/^(?:daje|zapewnia|dodaje|posiada|otrzymuje)\s+/i, '')
    if (hasLeadingItemStatDescription(withoutLeadIn, item.stats)) remaining = withoutLeadIn
  }

  let removedStat = true
  while (removedStat) {
    removedStat = false
    for (const [stat, value] of Object.entries(item.stats)) {
      const match = itemStatDescriptionPattern(stat, value)?.exec(remaining)
      if (!match) continue
      remaining = remaining.slice(match[0].length).replace(/^\s*(?:,\s*|\.\s*)/, '').trim()
      removedStat = true
      break
    }
  }

  const mechanic = remaining.replace(/^[,.;]\s*/, '').trim()
  return mechanic || undefined
}

const ITEM_TRIGGER_LABELS: Record<string, string> = {
  on_equip: 'Po założeniu',
  start_of_combat: 'Na początku walki',
  on_hit: 'Po trafieniu',
  on_attack: 'Przy ataku',
  on_bonus_attack: 'Przy bonusowym ataku',
  on_damage_dealt: 'Po zadaniu obrażeń',
  periodic_timer: 'Okresowo',
  on_self_hp_at_or_below_threshold: 'Po spadku HP do progu',
  on_ordinary_attack_count: 'Co określoną liczbę zwykłych ataków',
  on_mana_gain: 'Po uzyskaniu many',
  on_direct_hit_received: 'Po otrzymaniu bezpośredniego trafienia',
  on_ordinary_attack: 'Przy zwykłym ataku',
  start_of_combat_and_on_ally_death: 'Na początku walki i po śmierci sojusznika',
}

export const formatItemTrigger = (trigger: string) => ITEM_TRIGGER_LABELS[trigger] || trigger

export const getRecipePreview = (catalog: Item[], first: string, second: string) => {
  const pair = [first, second].sort().join('\u0000')
  return catalog.find(item => (
    item.kind === 'combined'
      && item.components.length === 2
      && item.components.slice().sort().join('\u0000') === pair
  ))
}

/**
 * Pure client-side projection of the backend equip_item contract.
 * The backend scans all equipped slots and replaces the last compatible base
 * item, so the preview must do the same without mutating player state.
 */
export const getUnitItemPreview = (
  catalog: Item[],
  equippedItemIds: string[],
  incomingItemId: string,
): ItemUnitPreview | null => {
  const itemById = new Map(catalog.map(item => [item.id, item]))
  const incomingItem = itemById.get(incomingItemId)
  if (!incomingItem) return null

  const nextItemIds = [...equippedItemIds]
  let resultingItem = incomingItem
  let replacedItemId: string | undefined
  let slotIndex: number | undefined

  if (incomingItem.kind === 'base') {
    for (let index = 0; index < nextItemIds.length; index += 1) {
      const equippedItem = itemById.get(nextItemIds[index])
      if (!equippedItem || equippedItem.kind !== 'base') continue
      const recipe = getRecipePreview(catalog, incomingItem.id, equippedItem.id)
      if (!recipe) continue
      // Keep scanning: the backend intentionally uses the last match.
      resultingItem = recipe
      replacedItemId = equippedItem.id
      slotIndex = index
    }
  }

  if (slotIndex !== undefined) {
    nextItemIds[slotIndex] = resultingItem.id
  } else if (nextItemIds.length < 3) {
    nextItemIds.push(incomingItem.id)
  } else {
    return {
      legal: false,
      incomingItem,
      resultingItem,
      nextItemIds,
      mode: 'blocked',
      statChanges: {},
      reason: 'Jednostka ma już 3 przedmioty',
    }
  }

  const statChanges: Record<string, number> = {}
  const addStats = (item: Item, multiplier: number) => {
    Object.entries(item.stats).forEach(([stat, value]) => {
      statChanges[stat] = (statChanges[stat] || 0) + value * multiplier
    })
  }
  if (replacedItemId) {
    const replacedItem = itemById.get(replacedItemId)
    if (replacedItem) addStats(replacedItem, -1)
    addStats(resultingItem, 1)
  } else {
    addStats(incomingItem, 1)
  }

  return {
    legal: true,
    incomingItem,
    resultingItem,
    nextItemIds,
    mode: replacedItemId ? 'auto-combine' : 'equip',
    replacedItemId,
    slotIndex,
    statChanges,
  }
}
