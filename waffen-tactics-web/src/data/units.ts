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
  skill?: {
    name: string
    description: string
    mana_cost?: number
    effects: any[]
  }
  stats?: {
    hp: number
    attack: number
    defense: number
    attack_speed: number
    max_mana?: number
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
    console.log(unitsArray);
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
  }
}

export function getUnit(unitId: string): Unit | undefined {
  return UNITS_CACHE[unitId] || FALLBACK_UNITS[unitId]
}

export function getAllUnits(): Unit[] {
  const cached = Object.values(UNITS_CACHE || {})
  const fallback = Object.values(FALLBACK_UNITS).filter(f => !cached.find(c => c.id === f.id))
  return [...cached, ...fallback]
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
