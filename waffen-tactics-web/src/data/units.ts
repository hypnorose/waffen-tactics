import axios from 'axios'

export interface Unit {
  id: string
  name: string
  cost: number
  factions: string[]
  classes: string[]
  role?: string
  role_color?: string
  avatar?: string
  stats?: {
    hp: number
    attack: number
    defense: number
    attack_speed: number
  }
}

let UNITS_CACHE: Record<string, Unit> = {}
let UNITS_LOADED = false

// Load units from API
export async function loadUnits(): Promise<void> {
  if (UNITS_LOADED) return
  
  try {
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const response = await axios.get(`${API_URL}/game/units`)
    const unitsArray: Unit[] = response.data
    
    UNITS_CACHE = {}
    unitsArray.forEach(unit => {
      UNITS_CACHE[unit.id] = unit
    })
    
    UNITS_LOADED = true
    console.log(`✅ Loaded ${unitsArray.length} units from API`)
  } catch (err) {
    console.error('Failed to load units:', err)
  }
}

// Fallback units for development
const FALLBACK_UNITS: Record<string, Unit> = {
  rafcikd: {
    id: 'rafcikd',
    name: 'RafcikD',
    cost: 1,
    factions: ['Denciak'],
    classes: ['Normik'],
    stats: { hp: 100, attack: 15, defense: 5, attack_speed: 1.0 }
  },
  falconbalkon: {
    id: 'falconbalkon',
    name: 'FalconBalkon',
    cost: 2,
    factions: ['Denciak'],
    classes: ['Gamer'],
    stats: { hp: 150, attack: 25, defense: 8, attack_speed: 1.2 }
  },
  piwniczak: {
    id: 'piwniczak',
    name: 'Piwniczak',
    cost: 2,
    factions: ['Denciak'],
    classes: ['Haker'],
    stats: { hp: 120, attack: 30, defense: 5, attack_speed: 0.9 }
  },
  capybara: {
    id: 'capybara',
    name: 'Capybara',
    cost: 3,
    factions: ['Denciak'],
    classes: ['Femboy'],
    stats: { hp: 200, attack: 35, defense: 12, attack_speed: 1.1 }
  },
  dyzma: {
    id: 'dyzma',
    name: 'Dyzma',
    cost: 3,
    factions: ['Denciak'],
    classes: ['Wojownik'],
    stats: { hp: 250, attack: 40, defense: 15, attack_speed: 0.8 }
  },
  smutny_dawid: {
    id: 'smutny_dawid',
    name: 'Smutny Dawid',
    cost: 4,
    factions: ['Lewo'],
    classes: ['Tank'],
    stats: { hp: 350, attack: 30, defense: 25, attack_speed: 0.7 }
  },
  veselymemes: {
    id: 'veselymemes',
    name: 'VeselyMemes',
    cost: 4,
    factions: ['Prawo'],
    classes: ['Snajper'],
    stats: { hp: 180, attack: 60, defense: 8, attack_speed: 1.5 }
  }
}

export function getUnit(unitId: string): Unit | undefined {
  return UNITS_CACHE[unitId] || FALLBACK_UNITS[unitId]
}

export function getCostColor(cost: number): string {
  if (cost === 1) return 'text-gray-400 border-gray-400'
  if (cost === 2) return 'text-green-400 border-green-400'
  if (cost === 3) return 'text-blue-400 border-blue-400'
  if (cost === 4) return 'text-purple-400 border-purple-400'
  return 'text-yellow-400 border-yellow-400'
}

export function getCostBorderColor(cost: number): string {
  if (cost === 1) return '#9ca3af'
  if (cost === 2) return '#4ade80'
  if (cost === 3) return '#60a5fa'
  if (cost === 4) return '#c084fc'
  return '#facc15'
}

export function getFactionColor(faction: string): string {
  const colors: Record<string, string> = {
    'Denciak': 'bg-gray-700',
    'Lewo': 'bg-red-700',
    'Prawo': 'bg-blue-700',
    'Centrum': 'bg-green-700'
  }
  return colors[faction] || 'bg-gray-700'
}
