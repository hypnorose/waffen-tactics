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
      const targetId = event.target_id
      const targetHp = event.target_hp
      const side = event.side
      if (targetId && typeof targetHp === 'number' && side) {
        if (side === 'team_a') {
          newState.playerUnits = updateUnitById(newState.playerUnits, targetId, u => ({ ...u, hp: targetHp }))
        } else {
          newState.opponentUnits = updateUnitById(newState.opponentUnits, targetId, u => ({ ...u, hp: targetHp }))
        }
      }
      break

    case 'unit_attack':
      if (event.target_id) {
        // Priority: Use authoritative HP fields from backend (unit_hp, target_hp, post_hp, new_hp)
        // Fallback: Calculate from damage delta (less reliable, may desync)
        let newHp: number | undefined
        if (event.unit_hp !== undefined) {
          newHp = event.unit_hp
        } else if (event.target_hp !== undefined) {
          newHp = event.target_hp
        } else if (event.post_hp !== undefined) {
          newHp = event.post_hp
        } else if (event.new_hp !== undefined) {
          newHp = event.new_hp
        }

        const shieldAbsorbed = event.shield_absorbed ?? 0

        if (newHp !== undefined) {
          // Use authoritative HP from backend
          const updateFn = (u: Unit) => {
            const newShield = Math.max(0, (u.shield || 0) - shieldAbsorbed)
            return { ...u, hp: newHp!, shield: newShield }
          }
          if (event.target_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.target_id, updateFn)
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.target_id, updateFn)
          }
        } else {
          // No authoritative HP provided — do NOT attempt local fallback calculation.
          // Preserve event-sourcing: missing fields should surface desyncs so upstream
          // bugs are fixed rather than masked here.
          console.warn(`⚠️ unit_attack event ${event.seq} missing authoritative HP - skipping local HP update`)
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
        let delta = 0

        // Priority: Use authoritative applied_delta from backend if available
        if (event.applied_delta !== undefined) {
          delta = event.applied_delta
        } else if (event.stat !== 'random') {
          // Fallback: Calculate delta locally (TEMPORARY - backend should always provide applied_delta)
          if (event.value_type === 'percentage') {
            const baseStat = event.stat === 'hp' ? 0 : (event.stat === 'attack' ? (event.unit_attack ?? 0) : (event.unit_defense ?? 0))
            delta = Math.floor(baseStat * (amountNum / 100))
          } else {
            delta = amountNum
          }
        }
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
        console.log(`[MANA] Event for ${event.unit_id}: current_mana=${event.current_mana}, amount=${event.amount}`)
        if (event.current_mana !== undefined && event.current_mana !== null) {
          // Absolute mana update (set to specific value)
          const updateFn = (u: Unit) => {
            console.log(`[MANA] Updating ${u.id} from ${u.current_mana} to ${event.current_mana}`)
            return { ...u, current_mana: event.current_mana }
          }
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
          }
          newState.combatLog = [...newState.combatLog, `🔮 ${event.unit_name} mana: ${event.current_mana}/${event.max_mana}`]
        } else if (event.amount !== undefined) {
          // Relative mana update (add/subtract amount)
          const amountNum = event.amount ?? 0
          const updateFn = (u: Unit) => {
            const cur = u.current_mana ?? 0
            const max = u.max_mana ?? Number.POSITIVE_INFINITY
            const newMana = Math.min(max, cur + amountNum)
            console.log(`[MANA] Updating ${u.id} from ${cur} by ${amountNum} to ${newMana}`)
            return { ...u, current_mana: newMana }
          }
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
          }
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
        // Priority: Use authoritative HP from backend (unit_hp, post_hp, new_hp)
        // Fallback: Calculate from delta (amount)
        let newHealHp: number | undefined
        if (event.unit_hp !== undefined) {
          newHealHp = event.unit_hp
        } else if (event.post_hp !== undefined) {
          newHealHp = event.post_hp
        } else if (event.new_hp !== undefined) {
          newHealHp = event.new_hp
        }

        if (newHealHp !== undefined) {
          // Use authoritative HP
          if (healSide === 'team_a') {
            newState.playerUnits = updateUnitById(newState.playerUnits, healUnitId, u => ({ ...u, hp: newHealHp! }))
          } else {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, healUnitId, u => ({ ...u, hp: newHealHp! }))
          }
        } else if (event.amount !== undefined) {
          // Fallback: incremental update
          const healAmount = event.amount
          if (healSide === 'team_a') {
            newState.playerUnits = updateUnitById(newState.playerUnits, healUnitId, u => ({ ...u, hp: Math.min(u.max_hp, u.hp + healAmount) }))
          } else {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, healUnitId, u => ({ ...u, hp: Math.min(u.max_hp, u.hp + healAmount) }))
          }
        }
      }
      break

    case 'unit_heal':
      if (event.unit_id) {
        let newHp: number
        // Priority: authoritative HP fields first (unit_hp, post_hp, new_hp), then fallback to incremental (amount)
        if (event.unit_hp !== undefined) {
          newHp = event.unit_hp
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, u => ({ ...u, hp: newHp }))
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, u => ({ ...u, hp: newHp }))
          }
        } else if (event.post_hp !== undefined) {
          newHp = event.post_hp
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, u => ({ ...u, hp: newHp }))
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, u => ({ ...u, hp: newHp }))
          }
        } else if (event.new_hp !== undefined) {
          newHp = event.new_hp
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, u => ({ ...u, hp: newHp }))
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, u => ({ ...u, hp: newHp }))
          }
        } else if (event.amount !== undefined) {
          // Fallback: incremental update (less reliable)
          const updateFn = (u: Unit) => ({ ...u, hp: Math.min(u.max_hp, u.hp + event.amount!) })
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateFn)
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateFn)
          }
          newHp = 0 // not used
        }
      }
      newState.combatLog = [...newState.combatLog, `💚 ${event.unit_name} regeneruje ${(event.amount ?? 0).toFixed(2)} HP`]
      break

    case 'hp_regen':
      if (event.unit_id) {
        // Use authoritative unit_hp field from canonical hp_regen event
        if (event.unit_hp !== undefined) {
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, u => ({ ...u, hp: event.unit_hp! }))
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, u => ({ ...u, hp: event.unit_hp! }))
          }
        } else if (event.post_hp !== undefined) {
          // Fallback to post_hp
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, u => ({ ...u, hp: event.post_hp! }))
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, u => ({ ...u, hp: event.post_hp! }))
          }
        }
      }
      // Only log significant regen amounts to avoid spam
      if ((event.amount ?? 0) >= 1) {
        newState.combatLog = [...newState.combatLog, `💚 ${event.unit_name} regeneruje ${(event.amount ?? 0).toFixed(2)} HP (${event.cause || 'passive'})`]
      }
      break

    case 'damage_over_time_tick':
      if (event.unit_id) {
        const updateFn = (u: Unit) => ({ ...u, hp: event.unit_hp ?? u.hp })
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
        // Update HP if provided
        if (event.unit_hp !== undefined) {
          const updateHpFn = (u: Unit) => ({ ...u, hp: event.unit_hp! })
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateHpFn)
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateHpFn)
          }
        }
      }
      break

    case 'effect_expired':
      console.log('[EFFECT_EXPIRED] Processing:', event)
      if (event.unit_id) {
        // Find and remove the effect, reverting its stat changes
        const removeAndRevertFn = (u: Unit) => {
          let expiredEffect: EffectSummary | undefined
          let remainingEffects = u.effects || []

          if (event.effect_id) {
            // Remove by ID
            expiredEffect = u.effects?.find(e => e.id === event.effect_id)
            remainingEffects = u.effects?.filter(e => e.id !== event.effect_id) || []
          } else {
            // Fallback: remove by matching properties (if no ID provided)
            // This is a hack for backend bugs where effect_id is missing
            expiredEffect = u.effects?.find(e => 
              e.stat === event.stat && 
              e.value === event.amount && 
              e.duration === event.duration
            )
            if (expiredEffect) {
              remainingEffects = u.effects?.filter(e => e !== expiredEffect) || []
            }
          }

          console.log('[EFFECT_EXPIRED] Found effect:', expiredEffect, 'remaining:', remainingEffects.length)

          if (!expiredEffect) {
            // Effect not found, just return unchanged
            console.log('[EFFECT_EXPIRED] Effect not found')
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

        // Update HP if provided (authoritative from backend)
        if (event.unit_hp !== undefined) {
          const updateHpFn = (u: Unit) => ({ ...u, hp: event.unit_hp! })
          if (event.unit_id.startsWith('opp_')) {
            newState.opponentUnits = updateUnitById(newState.opponentUnits, event.unit_id, updateHpFn)
          } else {
            newState.playerUnits = updateUnitById(newState.playerUnits, event.unit_id, updateHpFn)
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