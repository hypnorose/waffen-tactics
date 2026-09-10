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
