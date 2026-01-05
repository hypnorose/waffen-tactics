import { CombatState, CombatEvent, Unit, EffectSummary } from './types'

interface ApplyEventContext {
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

    case 'animation_start':
      // Add animation to active animations list for UI to render
      const anim = {
        id: event.event_id || `anim_${Date.now()}`,
        animation_type: event.animation_id || 'basic_attack',
        attacker_id: event.attacker_id,
        target_id: event.target_id,
        duration: event.duration || 0.3,
        start: Date.now()
      }
      newState.activeAnimations = [...(newState.activeAnimations || []), anim]
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
      // ==================================================================================
      // SNAPSHOTS ARE VALIDATION ONLY - DO NOT OVERWRITE UI STATE
      // ==================================================================================
      // The snapshot event is used for validation in useCombatOverlayLogic.ts:182-184
      // where compareCombatStates() detects desyncs between UI state and server state.
      //
      // We do NOT overwrite UI state with snapshot data here because:
      // 1. UI state MUST be reconstructable from events alone (event-sourcing principle)
      // 2. Overwriting masks bugs where events are missing or incorrect
      // 3. Validation comparison happens AFTER this handler in the combat loop
      //
      // If desyncs are detected, they will be logged by DesyncInspector, surfacing the
      // root cause (missing events, wrong event data, etc.) so it can be fixed properly.
      // ==================================================================================

      // IMPORTANT: Do NOT auto-expire effects here!
      // Effects should ONLY be removed when effect_expired events arrive from backend.
      // Auto-expiration based on simTime causes timing mismatches and desyncs.
      // The backend explicitly emits effect_expired events when effects truly expire.

      // Update metadata that doesn't come from events (synergies, traits, opponent info)
      if (event.synergies) newState.synergies = event.synergies
      if (event.traits) newState.traits = event.traits
      if (event.opponent) newState.opponentInfo = event.opponent

      // NOTE: We do NOT update unit HP, attack, defense, effects, etc. from snapshots
      // Those MUST come from events (unit_attack, stat_buff, shield_applied, etc.)
      // Validation comparison will happen in useCombatOverlayLogic.ts after this handler
      //
      // The old 'overwriteSnapshots' feature has been REMOVED because it:
      // - Violated event-sourcing principles
      // - Masked bugs where events were missing/wrong
      // - Made desyncs harder to diagnose
      break

    case 'attack':
      if (event.target_id && event.target_hp !== undefined) {
        // Use target_id prefix to determine which array, NOT side (side is attacker's side!)
        if (event.target_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.target_id, u => ({ ...u, hp: event.target_hp! }))
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.target_id, u => ({ ...u, hp: event.target_hp! }))
        }
      }
      break

    case 'unit_attack':
      if (event.target_id) {
        // Backend MUST provide target_hp - no fallback fields
        if (event.target_hp === undefined) {
          console.error(`⚠️ unit_attack event ${event.seq} missing required field: target_hp`)
          break
        }

        const shieldAbsorbed = event.shield_absorbed ?? 0
        const updateFn = (u: Unit) => {
          const newShield = Math.max(0, (u.shield || 0) - shieldAbsorbed)
          return { ...u, hp: event.target_hp!, shield: newShield }
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
      console.log('[STAT_BUFF] Event:', event)
      const statName = event.stat === 'attack' ? 'Ataku' : event.stat === 'defense' ? 'Obrony' : event.stat || 'Statystyki'
      const buffType = event.buff_type === 'debuff' ? '⬇️' : '⬆️'
      let reason = ''
      if (event.buff_type === 'debuff') reason = '(umiejętność)'
      else if (event.cause === 'kill') reason = '(zabity wróg)'
      const buffMsg = `${buffType} ${event.unit_name} ${event.buff_type === 'debuff' ? 'traci' : 'zyskuje'} ${event.amount} ${statName} ${reason}`
      newState.combatLog = [...newState.combatLog, buffMsg]
      if (event.unit_id) {
        const amountNum = event.amount ?? 0

        // Backend MUST provide applied_delta - no fallback calculations
        if (event.applied_delta === undefined) {
          console.error(`⚠️ stat_buff event ${event.seq} missing required field: applied_delta`)
          break
        }

        const delta = event.applied_delta
        // CRITICAL: Determine effect type by value sign (negative = debuff)
        // Backend sends type in the effect object itself, but we need to detect it here too
        const effectType = (amountNum < 0 || delta < 0) ? 'debuff' : 'buff'
        const effect: EffectSummary = {
          id: event.effect_id,
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
          // CRITICAL: Create NEW effects array to prevent shared references
          const newEffects = [...(u.effects || []), { ...effect }]
          let newU = { ...u, effects: newEffects }
          if (event.stat === 'hp') {
            newU.hp = Math.min(u.max_hp, u.hp + delta)
          } else if (event.stat === 'attack') {
            newU.attack = u.attack + delta
            // buffed_stats should reflect the NEW attack value after delta is applied
            newU.buffed_stats = { ...u.buffed_stats, attack: newU.attack }
          } else if (event.stat === 'defense') {
            newU.defense = (u.defense ?? 0) + delta
            // buffed_stats should reflect the NEW defense value after delta is applied
            newU.buffed_stats = { ...u.buffed_stats, defense: newU.defense }
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
      if (event.unit_id) {
        // Backend MUST provide current_mana - no incremental amount fallback
        if (event.current_mana === undefined || event.current_mana === null) {
          console.error(`⚠️ mana_update event ${event.seq} missing required field: current_mana (has amount=${event.amount})`)
          break
        }

        // CRITICAL: Also update HP from unit_hp field (mana_update events carry authoritative HP)
        const updateFn = (u: Unit) => {
          const updates: Partial<Unit> = { current_mana: event.current_mana }
          if (event.unit_hp !== undefined) {
            updates.hp = event.unit_hp
          }
          return { ...u, ...updates }
        }

        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
        }
        newState.combatLog = [...newState.combatLog, `🔮 ${event.unit_name} mana: ${event.current_mana}/${event.max_mana}`]
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
      if (event.state) {
        newState.finalState = event.state
        // Update units with final state to ensure UI shows correct final HP values
        if (event.state.player_units) {
          newState.playerUnits = event.state.player_units.map((u: any) => ({
            ...u,
            hp: u.hp,
            max_hp: u.max_hp,
            current_mana: u.current_mana,
            shield: u.shield,
            effects: u.effects || []
          }))
        }
        if (event.state.opponent_units) {
          newState.opponentUnits = event.state.opponent_units.map((u: any) => ({
            ...u,
            hp: u.hp,
            max_hp: u.max_hp,
            current_mana: u.current_mana,
            shield: u.shield,
            effects: u.effects || []
          }))
        }
      }
      break

    case 'heal':
      const healUnitId = event.unit_id
      const healSide = event.side
      if (healUnitId && healSide) {
        // Backend MUST provide post_hp - no fallback calculations
        if (event.post_hp === undefined) {
          console.error(`⚠️ heal event ${event.seq} missing required field: post_hp`)
          break
        }

        if (healSide === 'team_a') {
          newState.playerUnits = updateUnitById(newState.playerUnits, healUnitId, u => ({ ...u, hp: event.post_hp! }))
        } else {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, healUnitId, u => ({ ...u, hp: event.post_hp! }))
        }
      }
      break

    case 'unit_heal':
      if (event.unit_id) {
        // Backend MUST provide post_hp - no fallback calculations
        if (event.post_hp === undefined) {
          console.error(`⚠️ unit_heal event ${event.seq} missing required field: post_hp`)
          break
        }

        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, u => ({ ...u, hp: event.post_hp! }))
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, u => ({ ...u, hp: event.post_hp! }))
        }
      }
      newState.combatLog = [...newState.combatLog, `💚 ${event.unit_name} regeneruje ${(event.amount ?? 0).toFixed(2)} HP`]
      break

    case 'hp_regen':
      if (event.unit_id) {
        // Backend MUST provide post_hp - no fallback fields
        if (event.post_hp === undefined) {
          console.error(`⚠️ hp_regen event ${event.seq} missing required field: post_hp`)
          break
        }

        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, u => ({ ...u, hp: event.post_hp! }))
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, u => ({ ...u, hp: event.post_hp! }))
        }
      }
      // Only log significant regen amounts to avoid spam
      if ((event.amount ?? 0) >= 1) {
        newState.combatLog = [...newState.combatLog, `💚 ${event.unit_name} regeneruje ${(event.amount ?? 0).toFixed(2)} HP (${event.cause || 'passive'})`]
      }
      break

    case 'damage_over_time_tick':
      if (event.unit_id) {
        // Backend MUST provide post_hp (or unit_hp) - no fallback
        const authHp = event.post_hp ?? event.unit_hp
        if (authHp === undefined) {
          console.error(`⚠️ damage_over_time_tick event ${event.seq} missing required field: post_hp or unit_hp`)
          break
        }

        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, u => ({ ...u, hp: authHp }))
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, u => ({ ...u, hp: authHp }))
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

    case 'skill_cast':
      // Mana is already updated by the preceding mana_update event
      // Don't set mana to 0 here as it would override the correct value
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
            id: event.effect_id,
            type: 'shield',
            amount: event.amount,
            duration: event.duration,
            caster_name: event.caster_name,
            expiresAt: event.duration ? ctx.simTime + event.duration : undefined,
            applied_amount: event.amount
          }
          // CRITICAL: Create NEW effects array to prevent shared references
          const newEffects = [...(u.effects || []), { ...effect }]
          return { ...u, effects: newEffects, shield: Math.max(0, newShield) }
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
          id: event.effect_id,
          type: 'stun',
          duration: event.duration,
          caster_name: event.caster_name,
          expiresAt: event.duration ? ctx.simTime + event.duration : undefined
        }
        console.log(`[EFFECT DEBUG] Applying stun to ${event.unit_id}:`, effect)
        const updateFn = (u: Unit) => {
          // CRITICAL: Create NEW effects array to prevent shared references
          const newEffects = [...(u.effects || []), { ...effect }]
          console.log(`[EFFECT DEBUG] ${u.id} effects before: ${u.effects?.length || 0}, after: ${newEffects.length}`)
          return { ...u, effects: newEffects }
        }
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
          id: event.effect_id,
          type: 'damage_over_time',
          damage: event.damage || event.amount,
          duration: event.duration,
          ticks: event.ticks,
          interval: event.interval,
          caster_name: event.caster_name,
          expiresAt: event.duration ? ctx.simTime + event.duration : undefined
        }
        console.log(`[EFFECT DEBUG] Applying DoT to ${event.unit_id}:`, effect)
        const updateFn = (u: Unit) => {
          // CRITICAL: Create NEW effects array to prevent shared references
          const newEffects = [...(u.effects || []), { ...effect }]
          console.log(`[EFFECT DEBUG] ${u.id} effects before: ${u.effects?.length || 0}, after: ${newEffects.length}`)
          return { ...u, effects: newEffects }
        }
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
        }
      }
      break

    case 'damage_over_time_expired':
      if (event.unit_id) {
        // Backend MUST provide effect_id
        if (!event.effect_id) {
          console.error(`⚠️ damage_over_time_expired event ${event.seq} missing required field: effect_id`)
          break
        }

        // Remove the DoT effect by id
        const removeEffectFn = (u: Unit) => ({
          ...u,
          effects: u.effects?.filter(e => e.id !== event.effect_id) || []
        })
        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, removeEffectFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, removeEffectFn)
        }

        // Backend should provide post_hp for final HP after DoT expires
        const authHp = event.post_hp ?? event.unit_hp
        if (authHp !== undefined) {
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, u => ({ ...u, hp: authHp }))
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, u => ({ ...u, hp: authHp }))
          }
        }
      }
      break

    case 'effect_expired':
      console.log('[EFFECT_EXPIRED] Processing:', event)
      if (event.unit_id) {
        // Backend MUST provide effect_id - no property matching fallback
        if (!event.effect_id) {
          console.error(`⚠️ effect_expired event ${event.seq} missing required field: effect_id`)
          break
        }

        // Find and remove the effect, reverting its stat changes
        const removeAndRevertFn = (u: Unit) => {
          const expiredEffect = u.effects?.find(e => e.id === event.effect_id)
          const remainingEffects = u.effects?.filter(e => e.id !== event.effect_id) || []

          console.log('[EFFECT_EXPIRED] Found effect:', expiredEffect, 'remaining:', remainingEffects.length)

          if (!expiredEffect) {
            // Effect not found - this indicates a desync or missing effect application
            console.warn(`[EFFECT_EXPIRED] Effect ${event.effect_id} not found on unit ${u.id}`)
            return u
          }

          // Revert stat changes from the expired effect
          let newU = { ...u, effects: remainingEffects }

          if (expiredEffect.stat && expiredEffect.applied_delta !== undefined) {
            const delta = -expiredEffect.applied_delta  // Negative to revert
            console.log('[EFFECT_EXPIRED] Reverting stat:', expiredEffect.stat, 'delta:', delta)

            if (expiredEffect.stat === 'hp') {
              // Don't revert HP - backend sends authoritative HP in game_state
              // HP changes are permanent (damage taken, healing, etc.)
            } else if (expiredEffect.stat === 'attack') {
              newU.attack = (u.attack ?? 0) + delta
              newU.buffed_stats = { ...u.buffed_stats, attack: newU.attack }
            } else if (expiredEffect.stat === 'defense') {
              newU.defense = (u.defense ?? 0) + delta
              newU.buffed_stats = { ...u.buffed_stats, defense: newU.defense }
            }
          }

          return newU
        }

        if (event.unit_id.startsWith('opp_')) {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, removeAndRevertFn)
        } else {
          newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, removeAndRevertFn)
        }

        // Backend should provide post_hp for final HP after effect expires (optional for stat-only effects)
        const authHp = event.post_hp ?? event.unit_hp
        if (authHp !== undefined) {
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, u => ({ ...u, hp: authHp }))
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, u => ({ ...u, hp: authHp }))
          }
        }
      }
      break

    case 'skill_effect':
      // Log unknown skill effect application
      console.log(`[Skill Effect] ${event.caster_id} applied unknown effect:`, event.effect)
      break
  }

  // IMPORTANT: Do NOT auto-expire effects here!
  // Effects should ONLY be removed when effect_expired events arrive from backend.
  // Auto-expiration causes desyncs because frontend timing may differ from backend by a few ms.
  // The backend explicitly emits effect_expired events when effects truly expire.

  return newState
}

/**
 * CRITICAL: Deep copy helper to prevent shared reference bugs
 *
 * The spread operator creates SHALLOW copies, meaning nested arrays/objects are shared by reference.
 * This causes bugs where modifying effects/buffed_stats in one unit affects all previous snapshots.
 *
 * Example of the bug:
 *   const u1 = { id: 'test', effects: [{type: 'stun'}] }
 *   const u2 = { ...u1, hp: 100 }  // SHALLOW COPY!
 *   u2.effects.push({type: 'dot'})  // ALSO MODIFIES u1.effects!
 *
 * Solution: Always deep-copy nested objects when updating units.
 */
function deepCopyUnit(u: Unit): Unit {
  return {
    ...u,
    effects: u.effects ? [...u.effects] : [],
    buffed_stats: u.buffed_stats ? { ...u.buffed_stats } : {}
  }
}

function updateUnitById(units: Unit[], id: string, updater: (u: Unit) => Unit): Unit[] {
  return units.map(u => {
    if (u.id === id) {
      // Deep copy BEFORE passing to updater to prevent mutation
      const deepCopy = deepCopyUnit(u)
      const updated = updater(deepCopy)
      // Ensure nested objects are also deep copied in result
      return {
        ...updated,
        effects: updated.effects ? [...updated.effects] : [],
        buffed_stats: updated.buffed_stats ? { ...updated.buffed_stats } : {}
      }
    }
    return u
  })
}