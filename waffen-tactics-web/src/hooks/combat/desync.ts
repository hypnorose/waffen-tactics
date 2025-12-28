import { Unit, DesyncEntry, CombatEvent, CombatState } from './types'

export function compareUnits(localUnits: Unit[], serverUnits: any[], side: string, event: CombatEvent): DesyncEntry[] {
  const desyncs: DesyncEntry[] = []
  const localMap = new Map(localUnits.map(u => [u.id, {
    id: u.id,
    name: u.name,
    hp: u.hp,
    max_hp: u.max_hp,
    attack: u.attack,
    defense: u.defense ?? 0,
    attack_speed: u.buffed_stats?.attack_speed ?? 1,
    star_level: u.star_level,
    position: u.position ?? 'front',
    effects: canonicalizeEffects(u.effects ?? []),
    current_mana: u.current_mana ?? 0,
    max_mana: u.max_mana ?? 100,
    shield: u.shield ?? 0,
    buffed_stats: u.buffed_stats ?? {}
  }]))
  for (const su of serverUnits) {
    const lu = localMap.get(su.id)
    if (!lu) continue
    const diff: Record<string, { ui: any, server: any }> = {}
    const fields = ['hp', 'max_hp', 'attack', 'defense', 'attack_speed', 'current_mana', 'max_mana', 'shield']
    for (const f of fields) {
      if ((lu as any)[f] !== su[f]) diff[f] = { ui: (lu as any)[f], server: su[f] }
    }
    if (JSON.stringify(lu.buffed_stats) !== JSON.stringify(su.buffed_stats)) diff['buffed_stats'] = { ui: lu.buffed_stats, server: su.buffed_stats }
    if (JSON.stringify(lu.effects) !== JSON.stringify(canonicalizeEffects(su.effects ?? []))) diff['effects'] = { ui: lu.effects, server: canonicalizeEffects(su.effects ?? []) }
    if (Object.keys(diff).length > 0) {
      desyncs.push({
        unit_id: su.id,
        unit_name: su.name,
        seq: event.seq,
        timestamp: event.timestamp,
        diff,
        pending_events: [],
        note: `event ${event.type} diff (${side})`
      })
    }
  }
  return desyncs
}

export function compareCombatStates(localState: CombatState, serverState: any, event: CombatEvent): DesyncEntry[] {
  const desyncs: DesyncEntry[] = []

  // Compare only units
  const playerDesyncs = compareUnits(localState.playerUnits, serverState.player_units || [], 'player', event)
  const oppDesyncs = compareUnits(localState.opponentUnits, serverState.opponent_units || [], 'opponent', event)
  desyncs.push(...playerDesyncs, ...oppDesyncs)

  return desyncs
}

function canonicalizeEffects(effects: any[]): any[] {
  // Only log if effects are present to reduce console spam
  if (effects.length > 0) {
    // console.log(`[CANONICAL DEBUG] Canonicalizing effects:`, JSON.stringify(effects, null, 2))
  }

  const canonical = effects.map(e => ({
    id: e.id,
    type: e.type,
    stat: e.stat,
    value: e.value ?? e.amount,
    duration: e.duration
  })).sort((a, b) => (a.id || '').localeCompare(b.id || '') || a.type.localeCompare(b.type))

  if (effects.length > 0) {
    // console.log(`[CANONICAL DEBUG] Result:`, JSON.stringify(canonical, null, 2))
  }

  return canonical
}