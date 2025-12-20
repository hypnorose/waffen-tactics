import { CombatState, CombatEvent, Unit, EffectSummary } from './types'

interface ApplyEventContext {
  overwriteSnapshots: boolean
  simTime: number
}

export function applyCombatEvent(state: CombatState, event: CombatEvent, ctx: ApplyEventContext): CombatState {
  let newState = { ...state }

  // Update simTime if timestamp present
  if (typeof event.timestamp === 'number') {
    newState.simTime = event.timestamp
  }

  switch (event.type) {
    case 'start':
      newState.combatLog = [...newState.combatLog, '⚔️ Walka rozpoczyna się!']
      break

    case 'units_init':
      if (event.player_units) {
        const normalizedPlayers = event.player_units.map((u, idx) => ({
          ...u,
          hp: u.hp ?? 0,
          current_mana: u.current_mana ?? 0,
          shield: u.shield ?? 0,
          position: u.position ?? (idx < Math.ceil(event.player_units!.length / 2) ? 'front' : 'back')
        }))
        newState.playerUnits = normalizedPlayers
        console.log('Player units buffed_stats:', normalizedPlayers.map(u => ({ id: u.id, name: u.name, buffed_stats: u.buffed_stats })))
      }
      if (event.opponent_units) {
        const normalizedOpps = event.opponent_units.map((u, idx) => ({
          ...u,
          hp: u.hp ?? 0,
          current_mana: u.current_mana ?? 0,
          shield: u.shield ?? 0,
          position: u.position ?? (idx < Math.ceil(event.opponent_units!.length / 2) ? 'front' : 'back')
        }))
        newState.opponentUnits = normalizedOpps
      }
      if (event.synergies) newState.synergies = event.synergies
      if (event.traits) newState.traits = event.traits
      if (event.opponent) newState.opponentInfo = event.opponent
      break

    case 'state_snapshot':
      // Expire effects before updating
      const currentTime = ctx.simTime
      newState.playerUnits = newState.playerUnits.map(u => ({
        ...u,
        effects: u.effects?.filter(e => !e.expiresAt || e.expiresAt > currentTime) || []
      }))
      newState.opponentUnits = newState.opponentUnits.map(u => ({
        ...u,
        effects: u.effects?.filter(e => !e.expiresAt || e.expiresAt > currentTime) || []
      }))
      // Handle snapshot - overwrite if enabled
      if (event.player_units && ctx.overwriteSnapshots) {
        const normalizedPlayers = event.player_units.map((u, idx) => ({
          ...u,
          hp: u.hp ?? 0,
          current_mana: u.current_mana ?? 0,
          shield: u.shield ?? 0,
          position: u.position ?? (idx < Math.ceil(event.player_units!.length / 2) ? 'front' : 'back')
        }))
        const prevMap = new Map(newState.playerUnits.map(p => [p.id, p]))
        newState.playerUnits = normalizedPlayers.map(u => {
          const prevU = prevMap.get(u.id)
          return {
            ...u,
            avatar: prevU?.avatar || u.avatar || undefined,
            template_id: prevU?.template_id || u.template_id || undefined,
            factions: prevU?.factions || u.factions || undefined,
            classes: prevU?.classes || u.classes || undefined,
            skill: prevU?.skill || u.skill || undefined,
          }
        })
      }
      // Always update effects
      if (event.player_units) {
        newState.playerUnits = newState.playerUnits.map(u => {
          const serverU = event.player_units!.find(su => su.id === u.id)
          if (serverU) {
            return { ...u, effects: serverU.effects }
          }
          return u
        })
      }
      // Similar for opponent
      if (event.opponent_units && ctx.overwriteSnapshots) {
        const normalizedOpps = event.opponent_units.map((u, idx) => ({
          ...u,
          hp: u.hp ?? 0,
          current_mana: u.current_mana ?? 0,
          shield: u.shield ?? 0,
          position: u.position ?? (idx < Math.ceil(event.opponent_units!.length / 2) ? 'front' : 'back')
        }))
        const prevMap = new Map(newState.opponentUnits.map(p => [p.id, p]))
        newState.opponentUnits = normalizedOpps.map(u => {
          const prevU = prevMap.get(u.id)
          return {
            ...u,
            avatar: prevU?.avatar || u.avatar || undefined,
            template_id: prevU?.template_id || u.template_id || undefined,
            factions: prevU?.factions || u.factions || undefined,
            classes: prevU?.classes || u.classes || undefined,
            skill: prevU?.skill || u.skill || undefined,
          }
        })
      }
      if (event.opponent_units) {
        newState.opponentUnits = newState.opponentUnits.map(u => {
          const serverU = event.opponent_units!.find(su => su.id === u.id)
          if (serverU) {
            return { ...u, effects: serverU.effects }
          }
          return u
        })
      }
      if (event.synergies) newState.synergies = event.synergies
      if (event.traits) newState.traits = event.traits
      if (event.opponent) newState.opponentInfo = event.opponent
      break

    case 'attack':
      const targetId = event.target_id
      const targetHp = event.target_hp
      const shieldAbsorbed = event.shield_absorbed || 0
      const side = event.side
      if (targetId && typeof targetHp === 'number' && side) {
        if (side === 'team_a') {
          newState.playerUnits = updateUnitById(newState.playerUnits, targetId, u => ({ ...u, hp: targetHp, shield: Math.max(0, (u.shield || 0) - shieldAbsorbed) }))
        } else {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, targetId, u => ({ ...u, hp: targetHp, shield: Math.max(0, (u.shield || 0) - shieldAbsorbed) }))
        }
      }
      break

    case 'unit_attack':
      if (event.target_id && event.damage !== undefined) {
        const damage = event.damage
        const shieldAbsorbed = event.shield_absorbed || 0
        const hpDamage = damage - shieldAbsorbed
        const updateFn = (u: Unit) => {
          const oldHp = u.hp
          const newHp = Math.max(0, oldHp - hpDamage)
          const newShield = Math.max(0, (u.shield || 0) - shieldAbsorbed)
          return { ...u, hp: newHp, shield: newShield }
        }
        if (event.target_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.target_id, updateFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.target_id, updateFn)
        }
      }
      const msg = event.is_skill
        ? `🔥 ${event.attacker_name} zadaje ${event.damage?.toFixed(2)} obrażeń ${event.target_name} (umiejętność)`
        : `⚔️ ${event.attacker_name} atakuje ${event.target_name} (${(event.damage ?? 0).toFixed(2)} dmg)`
      newState.combatLog = [...newState.combatLog, msg]
      break

    case 'unit_died':
      if (event.unit_id) {
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, u => ({ ...u, hp: 0 }))
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, u => ({ ...u, hp: 0 }))
        }
      }
      newState.combatLog = [...newState.combatLog, `💀 ${event.unit_name} zostaje pokonany!`]
      break

    case 'gold_reward':
      newState.combatLog = [...newState.combatLog, `💰 ${event.unit_name} daje +${event.amount} gold (sojusznik umarł)`]
      break

    case 'stat_buff':
      const statName = event.stat === 'attack' ? 'Ataku' : event.stat === 'defense' ? 'Obrony' : event.stat || 'Statystyki'
      const buffType = event.buff_type === 'debuff' ? '⬇️' : '⬆️'
      let reason = ''
      if (event.buff_type === 'debuff') reason = '(umiejętność)'
      else if (event.cause === 'kill') reason = '(zabity wróg)'
      const buffMsg = `${buffType} ${event.unit_name} ${event.buff_type === 'debuff' ? 'traci' : 'zyskuje'} ${event.amount} ${statName} ${reason}`
      newState.combatLog = [...newState.combatLog, buffMsg]
      if (event.unit_id) {
        const amountNum = event.amount ?? 0
        let delta = 0
        if (event.stat !== 'random') {
          if (event.value_type === 'percentage') {
            const baseStat = event.stat === 'hp' ? 0 : (event.stat === 'attack' ? (event.unit_attack ?? 0) : (event.unit_defense ?? 0))
            delta = Math.floor(baseStat * (amountNum / 100))
          } else {
            delta = amountNum
          }
        }
        const effectType = event.buff_type === 'debuff' ? 'debuff' : 'buff'
        const effect: EffectSummary = {
          type: effectType,
          stat: event.stat,
          value: amountNum,
          value_type: event.value_type,
          duration: event.duration,
          permanent: event.permanent,
          source: event.source_id,
          expiresAt: event.duration ? ctx.simTime + event.duration : undefined,
          applied_delta: delta
        }
        const updateFn = (u: Unit) => {
          let newU = { ...u, effects: [...(u.effects || []), effect] }
          if (event.stat === 'hp') {
            newU.hp = Math.min(u.max_hp, u.hp + delta)
          } else if (event.stat === 'attack') {
            newU.attack = u.attack + delta
            newU.buffed_stats = { ...u.buffed_stats, attack: (u.buffed_stats?.attack ?? u.attack) + delta }
          } else if (event.stat === 'defense') {
            newU.defense = (u.defense ?? 0) + delta
            newU.buffed_stats = { ...u.buffed_stats, defense: (u.buffed_stats?.defense ?? u.defense ?? 0) + delta }
          }
          return newU
        }
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
        }
      }
      break

    case 'mana_update':
      if (event.unit_id && event.amount !== undefined) {
        const amountNum = event.amount ?? 0
        const updateFn = (u: Unit) => {
          const cur = u.current_mana ?? 0
          const max = u.max_mana ?? Number.POSITIVE_INFINITY
          return { ...u, current_mana: Math.min(max, cur + amountNum) }
        }
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
        }
      }
      break

    case 'victory':
      newState.combatLog = [...newState.combatLog, '🎉 ZWYCIĘSTWO!']
      newState.victory = true
      break

    case 'defeat':
      newState.combatLog = [...newState.combatLog, event.message || '💔 PRZEGRANA!']
      newState.victory = false
      newState.defeatMessage = event.message
      break

    case 'end':
      newState.isFinished = true
      if (event.state) newState.finalState = event.state
      break

    case 'heal':
      const healUnitId = event.unit_id
      const healAmount = event.amount
      const healSide = event.side
      if (healUnitId && typeof healAmount === 'number' && healSide) {
        if (healSide === 'team_a') {
          newState.playerUnits = updateUnitById(newState.playerUnits, healUnitId, u => ({ ...u, hp: Math.min(u.max_hp, u.hp + healAmount) }))
        } else {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, healUnitId, u => ({ ...u, hp: Math.min(u.max_hp, u.hp + healAmount) }))
        }
      }
      break

    case 'unit_heal':
      if (event.unit_id) {
        let newHp: number
        if (event.amount !== undefined) {
          const updateFn = (u: Unit) => ({ ...u, hp: Math.min(u.max_hp, u.hp + event.amount!) })
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
          }
          newHp = 0 // not used
        } else if (event.unit_hp !== undefined) {
          newHp = event.unit_hp
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, u => ({ ...u, hp: newHp }))
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, u => ({ ...u, hp: newHp }))
          }
        }
      }
      newState.combatLog = [...newState.combatLog, `💚 ${event.unit_name} regeneruje ${(event.amount ?? 0).toFixed(2)} HP`]
      break

    case 'damage_over_time_tick':
      if (event.unit_id && event.damage !== undefined) {
        const updateFn = (u: Unit) => ({ ...u, hp: Math.max(0, u.hp - event.damage!) })
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
        }
      }
      newState.combatLog = [...newState.combatLog, `🔥 ${event.unit_name} otrzymuje ${event.damage ?? 0} obrażeń (DoT)`]
      break

    case 'regen_gain':
      if (event.unit_id) {
        const dur = event.duration || 5
        const expiresAt = ctx.simTime + dur // Use simTime for expiry
        newState.regenMap = { ...newState.regenMap, [event.unit_id]: { amount_per_sec: event.amount_per_sec || 0, total_amount: event.total_amount || 0, expiresAt } }
        newState.combatLog = [...newState.combatLog, `💚 ${event.unit_name} zyskuje +${(event.total_amount || 0).toFixed(2)} HP przez ${dur}s`]
      }
      break

    case 'mana_update':
      if (event.unit_id && event.current_mana !== undefined) {
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, u => ({ ...u, current_mana: event.current_mana }))
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, u => ({ ...u, current_mana: event.current_mana }))
        }
      }
      newState.combatLog = [...newState.combatLog, `🔮 ${event.unit_name} mana: ${event.current_mana}/${event.max_mana}`]
      break

    case 'skill_cast':
      if (event.caster_id) {
        const updateFn = (u: Unit) => ({ ...u, current_mana: 0 })
        if (event.caster_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.caster_id, updateFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.caster_id, updateFn)
        }
      }
      if (event.target_id && event.target_hp !== undefined) {
        if (event.target_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.target_id, u => ({ ...u, hp: event.target_hp! }))
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.target_id, u => ({ ...u, hp: event.target_hp! }))
        }
      }
      newState.combatLog = [...newState.combatLog, `✨ ${event.caster_name} używa ${event.skill_name}!`]
      break

    case 'shield_applied':
      if (event.unit_id && typeof event.amount === 'number') {
        const updateFn = (u: Unit) => {
          const newShield = (u.shield || 0) + event.amount!
          const effect: EffectSummary = {
            type: 'shield',
            amount: event.amount,
            duration: event.duration,
            caster_name: event.caster_name,
            expiresAt: event.duration ? ctx.simTime + event.duration : undefined,
            applied_amount: event.amount
          }
          return { ...u, effects: [...(u.effects || []), effect], shield: Math.max(0, newShield) }
        }
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
        }
      }
      newState.combatLog = [...newState.combatLog, `🛡️ ${event.unit_name} zyskuje ${event.amount} tarczy na ${event.duration}s`]
      break

    case 'unit_stunned':
      newState.combatLog = [...newState.combatLog, `😵 ${event.unit_name} jest ogłuszony na ${event.duration}s`]
      if (event.unit_id) {
        const effect: EffectSummary = {
          type: 'stun',
          duration: event.duration,
          caster_name: event.caster_name,
          expiresAt: event.duration ? ctx.simTime + event.duration : undefined
        }
        const updateFn = (u: Unit) => ({ ...u, effects: [...(u.effects || []), effect] })
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
        }
      }
      break

    case 'damage_over_time_applied':
      newState.combatLog = [...newState.combatLog, `🔥 ${event.unit_name} otrzymuje DoT (${event.ticks || '?'} ticks)`]
      if (event.unit_id) {
        const effect: EffectSummary = {
          type: 'damage_over_time',
          damage: event.damage || event.amount,
          duration: event.duration,
          ticks: event.ticks,
          interval: event.interval,
          caster_name: event.caster_name,
          expiresAt: event.duration ? ctx.simTime + event.duration : undefined
        }
        const updateFn = (u: Unit) => ({ ...u, effects: [...(u.effects || []), effect] })
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
        }
      }
      break

    default:
      // Unknown event, ignore
      break
  }

  return newState
}

function updateUnitById(units: Unit[], id: string, updater: (u: Unit) => Unit): Unit[] {
  return units.map(u => u.id === id ? updater(u) : u)
}