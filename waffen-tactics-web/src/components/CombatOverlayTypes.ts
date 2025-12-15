import { PlayerState } from '../store/gameStore'

export interface Unit {
  id: string
  name: string
  hp: number
  max_hp: number
  attack: number
  star_level: number
  cost?: number
  factions?: string[]
  classes?: string[]
  buffed_stats?: {
    hp?: number
    attack?: number
    defense?: number
    attack_speed?: number
    max_mana?: number
  }
}

export interface TraitDefinition {
  name: string
  type: string
  thresholds: number[]
  effects: any[]
}

export interface CombatEvent {
  type: string
  message?: string
  player_units?: Unit[]
  opponent_units?: Unit[]
  synergies?: Record<string, {count: number, tier: number}>
  traits?: TraitDefinition[]
  opponent?: {name: string, wins: number, level: number}
  attacker_id?: string
  target_id?: string
  damage?: number
  target_hp?: number
  target_max_hp?: number
  unit_id?: string
  round?: number
  state?: PlayerState
  amount_per_sec?: number
  total_amount?: number
  duration?: number
}

export interface CombatOverlayProps {
  onClose: (newState?: PlayerState) => void
}

export interface SynergiesPanelProps {
  synergies: Record<string, {count: number, tier: number}>
  traits: TraitDefinition[]
  hoveredTrait: string | null
  setHoveredTrait: (trait: string | null) => void
}

export interface CombatSpeedSliderProps {
  combatSpeed: number
  setCombatSpeed: (speed: number) => void
}

export interface CombatLogModalProps {
  showLog: boolean
  setShowLog: (show: boolean) => void
  combatLog: CombatEvent[]
  logEndRef: React.RefObject<HTMLDivElement>
}