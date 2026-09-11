import axios from 'axios'
import { API_BASE_URL } from '../services/apiBaseUrl'

export interface UnitPassive {
  name?: string
  title?: string
  description: string
  kind?: string
  [key: string]: any
}

export interface Unit {
  id: string
  name: string
  cost: number
  factions: string[]
  classes: string[]
  traits?: string[]
  role?: string
  role_color?: string
  avatar?: string
  max_mana?: number
  skill?: {
    name: string
    description: string
    mana_cost?: number
    effects: any[]
  }
  passive?: UnitPassive
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
    const response = await axios.get(`${API_BASE_URL}/game/units`)
    const unitsArray: Unit[] = response.data
    if (!Array.isArray(unitsArray)) {
      throw new Error('Canonical units API returned a non-array payload')
    }
    // console.log(unitsArray);
    UNITS_CACHE = {}
    unitsArray.forEach(unit => {
      UNITS_CACHE[unit.id] = unit
    })
    
    UNITS_LOADED = true
    // console.log(`✅ Loaded ${unitsArray.length} units from API`)
  } catch (err) {
    console.error('Failed to load units:', err)
    throw err
  }
}

export function getUnit(unitId: string): Unit | undefined {
  return UNITS_CACHE[unitId]
}

export function getPassiveTitle(passive?: UnitPassive): string | null {
  const candidate = passive?.name ?? passive?.title
  return typeof candidate === 'string' && candidate.trim().length > 0
    ? candidate.trim()
    : null
}

export function getAllUnits(): Unit[] {
  return Object.values(UNITS_CACHE)
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
