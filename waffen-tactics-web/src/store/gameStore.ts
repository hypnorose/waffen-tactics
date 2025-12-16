import { create } from 'zustand'

export interface Unit {
  id: string
  name: string
  cost: number
  factions: string[]
  classes: string[]
  stats: {
    hp: number
    attack: number
    defense: number
    attack_speed: number
  }
}

export interface UnitInstance {
  instance_id: string
  unit_id: string
  star_level: number
  position: 'front' | 'back'
}

export interface Synergy {
  name: string
  count: number
  tier: number
  thresholds: number[]
  active: boolean
  description?: string
  effects?: any[]
}

export interface PlayerState {
  hp: number
  level: number
  xp: number
  gold: number
  round_number: number
  wins: number
  losses: number
  streak: number
  board: UnitInstance[]
  bench: UnitInstance[]
  last_shop: string[]
  locked_shop: boolean
  max_board_size: number
  max_bench_size: number
  xp_to_next_level: number
  shop_odds: number[]
  synergies: Synergy[]
}

interface GameState {
  playerState: PlayerState | null
  units: Unit[]
  isLoading: boolean
  error: string | null
  setPlayerState: (state: PlayerState) => void
  setUnits: (units: Unit[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  detailedView: boolean
  setDetailedView: (detailed: boolean) => void
}

export const useGameStore = create<GameState>((set) => ({
  playerState: null,
  units: [],
  isLoading: false,
  error: null,
  setPlayerState: (playerState) => set({ playerState }),
  setUnits: (units) => set({ units }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  detailedView: false,
  setDetailedView: (detailed: boolean) => set({ detailedView: detailed }),
}))
