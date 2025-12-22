export interface Unit {
  id: string
  name: string
  hp: number
  max_hp: number
  shield?: number
  attack: number
  defense?: number
  star_level: number
  cost?: number
  factions?: string[]
  classes?: string[]
  position?: string
  template_id?: string
  buffed_stats?: {
    hp?: number
    attack?: number
    defense?: number
    attack_speed?: number
    max_mana?: number
  }
  current_mana?: number
  max_mana?: number
  effects?: EffectSummary[]
  persistent_buffs?: Record<string, number>
  avatar?: string
  skill?: any
}

export interface DesyncEntry {
  unit_id: string
  unit_name?: string
  seq?: number | null
  timestamp?: number | null
  diff: Record<string, { ui: any, server: any }>
  pending_events: CombatEvent[]
  note?: string
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
  synergies?: Record<string, { count: number, tier: number }>
  traits?: TraitDefinition[]
  opponent?: { name: string, wins: number, level: number, avatar?: string }
  attacker_id?: string
  target_id?: string
  damage?: number
  unit_hp?: number
  target_hp?: number
  target_max_hp?: number
  unit_id?: string
  post_hp?: number  // Authoritative HP after event (for heals, damage)
  pre_hp?: number   // HP before event
  new_hp?: number   // Alternative authoritative HP field (legacy)
  round?: number
  state?: any // PlayerState
  amount_per_sec?: number
  total_amount?: number
  timestamp?: number
  seq?: number
  // Mana and skill casting events
  caster_id?: string
  caster_name?: string
  skill_name?: string
  current_mana?: number
  max_mana?: number
  // Additional properties for various events
  attacker_name?: string
  target_name?: string
  unit_name?: string
  amount?: number
  stat?: string
  side?: string
  is_skill?: boolean
  buff_type?: string
  duration?: number
  shield_absorbed?: number
  cause?: string
  ticks?: number
  interval?: number
  game_state?: { player_units: any[], opponent_units: any[] }
  // Extended/optional fields used by applyEvent handlers
  value_type?: string
  unit_attack?: number
  unit_defense?: number
  permanent?: boolean
  source_id?: string
  effect_id?: string
  effect?: any
  applied_delta?: number  // Authoritative delta applied by backend (for stat_buff events)
}

export interface EffectSummary {
  id?: string
  type: string
  amount?: number
  stat?: string
  duration?: number
  expiresAt?: number
  ticks?: number
  interval?: number
  damage?: number
  caster_name?: string
  applied_delta?: number
  applied_amount?: number
  value?: number
  value_type?: string
  permanent?: boolean
  source?: string
}

export interface CombatState {
  playerUnits: Unit[]
  opponentUnits: Unit[]
  combatLog: string[]
  isFinished: boolean
  victory: boolean | null
  finalState: any | null
  synergies: Record<string, { count: number, tier: number }>
  traits: TraitDefinition[]
  opponentInfo: { name: string, wins: number, level: number } | null
  regenMap: Record<string, { amount_per_sec: number; total_amount: number; expiresAt: number }>
  simTime: number
  defeatMessage?: string
}