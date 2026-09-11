import { CombatState, CombatEvent, Unit, EffectSummary } from './types'
import { createCombatSummary, formatCombatLogEntry, updateCombatSummary } from './combatPresentation'

interface ApplyEventContext {
  simTime: number
}

export class CombatReplayValidationError extends Error {
  readonly eventType: string
  readonly unitId?: string
  readonly seq?: number

  constructor(event: CombatEvent, reason: string, unitId?: string) {
    super(`[REPLAY_VALIDATION] ${event.type} event seq=${event.seq ?? 'unknown'} ${reason}`)
    this.name = 'CombatReplayValidationError'
    this.eventType = event.type
    this.unitId = unitId
    this.seq = event.seq
  }
}

function isUnitDead(state: CombatState, unitId: string): boolean {
  const unit = [...state.playerUnits, ...state.opponentUnits].find(u => u.id === unitId)
  return Boolean(unit && unit.hp <= 0)
}

function requireKnownUnit(state: CombatState, event: CombatEvent, unitId: string | undefined): Unit {
  if (!unitId || !unitId.trim()) {
    throw new CombatReplayValidationError(event, 'missing required unit_id')
  }

  const unit = [...state.playerUnits, ...state.opponentUnits].find(candidate => candidate.id === unitId)
  if (!unit) {
    throw new CombatReplayValidationError(event, `references unknown unit_id=${unitId}`, unitId)
  }

  return unit
}

function requireEffectId(
  event: CombatEvent,
  effectId: unknown = event.effect_id,
  field = 'effect_id'
): string {
  if (typeof effectId !== 'string' || !effectId.trim()) {
    throw new CombatReplayValidationError(event, `missing required ${field}`, event.unit_id)
  }

  return effectId
}

function validateItemEventContext(event: CombatEvent): void {
  const hasItemContext = event.item_id !== undefined || event.item_effect_id !== undefined
  if (!hasItemContext) return

  for (const [field, value] of [
    ['item_id', event.item_id],
    ['item_effect_id', event.item_effect_id],
  ] as const) {
    if (typeof value !== 'string' || !value.trim()) {
      throw new CombatReplayValidationError(event, `item context requires non-empty string ${field}`, event.unit_id)
    }
  }
}

function itemEffectContext(event: CombatEvent): Partial<EffectSummary> {
  if (event.item_id === undefined) return {}
  return {
    item_id: event.item_id,
    item_effect_id: event.item_effect_id,
    item_effect: event.item_effect,
    stack: event.stack,
    stacks: event.stacks,
    stack_cap: event.stack_cap,
    value_before: event.value_before,
    value_after: event.value_after,
  }
}

function updateKnownUnitById(
  state: CombatState,
  event: CombatEvent,
  unitId: string | undefined,
  updater: (unit: Unit) => Unit
): void {
  requireKnownUnit(state, event, unitId)

  if (state.playerUnits.some(unit => unit.id === unitId)) {
    state.playerUnits = updateUnitById(state.playerUnits, unitId!, updater)
    return
  }

  state.opponentUnits = updateUnitById(state.opponentUnits, unitId!, updater)
}

function hasCanonicalPositions(units: Unit[] | undefined, side: string, seq?: number): boolean {
  if (!units) return true

  const invalidUnit = units.find(u => u.position !== 'front' && u.position !== 'back')
  if (!invalidUnit) return true

  console.error(
    `⚠️ units_init event ${seq} missing valid canonical position for ${side} unit ${invalidUnit.id}`
  )
  return false
}

export function applyCombatEvent(state: CombatState, event: CombatEvent, ctx: ApplyEventContext): CombatState {
  validateItemEventContext(event)

  if (event.type === 'formation_changed') {
    if (typeof event.event_id !== 'string' || !event.event_id.trim()) {
      throw new CombatReplayValidationError(event, 'missing required event_id', event.unit_id)
    }

    const applied = state.appliedFormationEvents?.[event.event_id]
    if (applied) {
      if (applied.unitId !== event.unit_id ||
          applied.previousPosition !== event.previous_position ||
          applied.newPosition !== event.new_position) {
        throw new CombatReplayValidationError(
          event,
          `conflicting duplicate event_id=${event.event_id}`,
          event.unit_id,
        )
      }
      // A reconnect may deliver the exact committed event more than once. Do
      // not advance time or append a second presentation log entry.
      return state
    }
  }

  let newState = { ...state }
  const logLine = formatCombatLogEntry(event)
  let shouldUpdateSummary = true

  // Update simTime if timestamp present
  if (typeof event.timestamp === 'number') {
    newState.simTime = event.timestamp
  }

  // Death is authoritative. Ignore late replay/SSE events for dead units.
  const stateChangingTypes = new Set([
    'attack', 'unit_attack', 'mana_update', 'stat_buff', 'shield_applied',
    'shield_broken', 'unit_stunned', 'damage_over_time_applied',
    'damage_over_time_tick', 'damage_over_time_expired', 'effect_applied', 'effect_expired',
    'unit_heal', 'heal', 'hp_regen', 'regen_gain', 'formation_changed'
  ])
  const involvedIds = [event.unit_id, event.attacker_id, event.target_id].filter(
    (id): id is string => Boolean(id)
  )
  if (stateChangingTypes.has(event.type) && involvedIds.some(id => isUnitDead(state, id))) {
    return newState
  }

  switch (event.type) {
    case 'start':
      if (logLine) newState.combatLog = [...newState.combatLog, logLine]
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
      if (!hasCanonicalPositions(event.player_units, 'player', event.seq) ||
          !hasCanonicalPositions(event.opponent_units, 'opponent', event.seq)) {
        shouldUpdateSummary = false
        break
      }
      if (event.player_units) {
        const normalizedPlayers = event.player_units.map(u => ({
          ...u,
          hp: u.hp ?? 0,
          current_mana: u.current_mana ?? 0,
          shield: u.shield ?? 0
        }))
        newState.playerUnits = normalizedPlayers
        console.log('🟢 [UNITS_INIT] Player units:', normalizedPlayers.map(u => ({ id: u.id, name: u.name, hp: u.hp, has_hp_field: 'hp' in u })))
        console.log('Player units buffed_stats:', normalizedPlayers.map(u => ({ id: u.id, name: u.name, buffed_stats: u.buffed_stats })))
      }
      if (event.opponent_units) {
        const normalizedOpps = event.opponent_units.map(u => ({
          ...u,
          hp: u.hp ?? 0,
          current_mana: u.current_mana ?? 0,
          shield: u.shield ?? 0
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
      // The snapshot event is used for validation in useCombatOverlayLogic.ts
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

      // Update metadata that doesn't come from events (synergies, traits, opponent info)
      if (event.synergies) newState.synergies = event.synergies
      if (event.traits) newState.traits = event.traits
      if (event.opponent) newState.opponentInfo = event.opponent

      // NOTE: We do NOT update unit HP, attack, defense, effects, etc. from snapshots
      // Those MUST come from events (unit_attack, stat_buff, shield_applied, etc.)
      // Backend MUST emit granular events for all state changes (hp, defense, effects)
      // Validation comparison will happen in useCombatOverlayLogic.ts after this handler
      break

    case 'attack':
      if (event.target_id) {
        requireKnownUnit(newState, event, event.target_id)
        if (event.target_hp === undefined || event.target_hp === null) {
          console.error(`⚠️ attack event ${event.seq} missing required field: target_hp`)
          shouldUpdateSummary = false
          break
        }
        updateKnownUnitById(newState, event, event.target_id, u => ({ ...u, hp: event.target_hp! }))
      }
      break

    case 'unit_attack':
      // Validate every supplied identity before applying the optional attacker mana update.
      if (event.attacker_id) requireKnownUnit(newState, event, event.attacker_id)
      if (event.target_id) requireKnownUnit(newState, event, event.target_id)
      if (event.target_id && (event.target_hp === undefined || event.target_hp === null)) {
        console.error(`⚠️ unit_attack event ${event.seq} missing required field: target_hp`)
        shouldUpdateSummary = false
        break
      }
      const hasCanonicalPostShield = event.post_shield !== undefined && event.post_shield !== null
      if (hasCanonicalPostShield && (typeof event.post_shield !== 'number' || !Number.isFinite(event.post_shield))) {
        console.error(`⚠️ unit_attack event ${event.seq} has invalid canonical post_shield`)
        shouldUpdateSummary = false
        break
      }
      if (event.attacker_id && event.attacker_current_mana !== undefined) {
        const attackerUpdate = (u: Unit) => ({
          ...u,
          current_mana: event.attacker_current_mana,
          max_mana: event.attacker_max_mana ?? u.max_mana,
        })
        updateKnownUnitById(newState, event, event.attacker_id, attackerUpdate)
      }

      if (event.target_id) {
        const shieldAbsorbed = event.shield_absorbed ?? 0
        if (shieldAbsorbed > 0 && !hasCanonicalPostShield) {
          console.error(`⚠️ unit_attack event ${event.seq} missing required field: post_shield for shield absorption`)
          shouldUpdateSummary = false
          break
        }
        const updateFn = (u: Unit) => {
          // Shield absorption is explanatory metadata. The server's canonical
          // post-state is authoritative; with no absorption, preserve the
          // existing shield when older payloads lack the optional field.
          const newShield = hasCanonicalPostShield ? event.post_shield! : u.shield
          return { ...u, hp: event.target_hp!, shield: newShield }
        }

        updateKnownUnitById(newState, event, event.target_id, updateFn)
      }
      if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      break

    case 'unit_died':
      updateKnownUnitById(newState, event, event.unit_id, u => ({ ...u, hp: 0 }))
      if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      break

    case 'formation_changed': {
      const unit = requireKnownUnit(newState, event, event.unit_id)
      const previousPosition = event.previous_position
      const newPosition = event.new_position
      if ((previousPosition !== 'front' && previousPosition !== 'back') ||
          (newPosition !== 'front' && newPosition !== 'back')) {
        throw new CombatReplayValidationError(event, 'requires canonical previous_position and new_position', event.unit_id)
      }
      if (previousPosition === newPosition) {
        throw new CombatReplayValidationError(event, 'requires a real position transition', event.unit_id)
      }
      if (unit.position !== previousPosition) {
        throw new CombatReplayValidationError(
          event,
          `position mismatch: expected current=${previousPosition}, actual=${unit.position}`,
          event.unit_id,
        )
      }
      updateKnownUnitById(newState, event, event.unit_id, u => ({ ...u, position: newPosition }))
      newState.appliedFormationEvents = {
        ...(newState.appliedFormationEvents || {}),
        [event.event_id!]: {
          unitId: event.unit_id!,
          previousPosition,
          newPosition,
        },
      }
      if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      break
    }

    case 'gold_reward':
      if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      break

    case 'gold_income':
    case 'skill_cast':
    case 'passive_triggered':
      // These events carry presentation/metadata information handled outside
      // the reducer; they intentionally do not mutate combat unit state.
      break

    case 'stat_buff':
      console.log('[STAT_BUFF] Event:', event)
      if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      requireKnownUnit(newState, event, event.unit_id)
      if (event.unit_id) {
        const statBuffEffectId = requireEffectId(event)
        const amountNum = event.amount ?? 0

        // Backend MUST provide applied_delta - no fallback calculations
        if (event.applied_delta === undefined) {
          console.error(`⚠️ [DESYNC] stat_buff event seq=${event.seq} missing CRITICAL field: applied_delta (unit=${event.unit_id}, stat=${event.stat})`)
          shouldUpdateSummary = false
          break
        }
        if (event.stat === 'max_hp' && (event.post_hp === undefined || event.post_hp === null)) {
          console.error(`⚠️ stat_buff event ${event.seq} missing required field: post_hp for max_hp mutation`)
          shouldUpdateSummary = false
          break
        }

        const delta = event.applied_delta
        // CRITICAL: Determine effect type by value sign (negative = debuff)
        // Backend sends type in the effect object itself, but we need to detect it here too
        const effectType = (amountNum < 0 || delta < 0) ? 'debuff' : 'buff'
        const effect: EffectSummary = {
          id: statBuffEffectId,
          type: effectType,
          ...itemEffectContext(event),
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
          // SSE reconnects and replay recovery may deliver an already applied
          // event again. Effect IDs make stat mutations idempotent.
          if (effect.id && (u.effects || []).some(existing => existing.id === effect.id)) {
            return u
          }
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
          } else if (event.stat === 'attack_speed') {
            newU.attack_speed = (u.attack_speed ?? 0) + delta
            newU.buffed_stats = { ...u.buffed_stats, attack_speed: newU.attack_speed }
          } else if (event.stat === 'max_hp') {
            // Max HP changes carry the backend's authoritative post_hp.
            // Recomputing the health ratio here would duplicate game logic.
            newU.max_hp = Math.max(0, (u.max_hp ?? 0) + delta)
            newU.hp = Math.min(newU.max_hp, Math.max(0, event.post_hp!))
            newU.buffed_stats = { ...u.buffed_stats, hp: newU.max_hp }
          }
          return newU
        }
        updateKnownUnitById(newState, event, event.unit_id, updateFn)

      }
      break

    case 'mana_update':
      requireKnownUnit(newState, event, event.unit_id)
      if (event.unit_id) {
        // Backend MUST provide current_mana - no incremental amount fallback
        if (event.current_mana === undefined || event.current_mana === null) {
          console.error(`⚠️ [DESYNC] mana_update event seq=${event.seq} missing CRITICAL field: current_mana (unit=${event.unit_id})`)
          shouldUpdateSummary = false
          break
        }
        const currentMana = Number(event.current_mana)

        // Debug: Log ALL mana_update events (brief format)
        console.log(`💠 MANA seq=${event.seq} ${event.unit_id}=${event.current_mana} amt=${event.amount}`)

        // Find unit BEFORE update
        const unitBefore = [...newState.playerUnits, ...newState.opponentUnits].find(u => u.id === event.unit_id)

          const updateFn = (u: Unit) => {
          const updates: Partial<Unit> = { current_mana: currentMana }
          // max_mana is authoritative too. Keeping it in the unit snapshot
          // prevents stale mana bars and fixes log/state divergence after a
          // class or passive changes the mana profile.
          if (typeof event.max_mana === 'number' && Number.isFinite(event.max_mana) && event.max_mana >= 0) {
            updates.max_mana = event.max_mana
            updates.current_mana = Math.max(0, Math.min(currentMana, event.max_mana))
          }
          const result = { ...u, ...updates }
          return result
        }

        updateKnownUnitById(newState, event, event.unit_id, updateFn)

        if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      }
      break

    case 'victory':
      if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      newState.victory = true
      break

    case 'defeat':
      if (logLine) newState.combatLog = [...newState.combatLog, logLine]
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
      requireKnownUnit(newState, event, healUnitId)
      if (healUnitId && healSide) {
        // Backend MUST provide post_hp - no fallback calculations
        if (event.post_hp === undefined || event.post_hp === null) {
          console.error(`⚠️ heal event ${event.seq} missing required field: post_hp`)
          shouldUpdateSummary = false
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
      requireKnownUnit(newState, event, event.unit_id)
      // Backend MUST provide post_hp - no fallback calculations
      if (event.post_hp === undefined || event.post_hp === null) {
        console.error(`⚠️ unit_heal event ${event.seq} missing required field: post_hp`)
        shouldUpdateSummary = false
        break
      }
      updateKnownUnitById(newState, event, event.unit_id, u => ({ ...u, hp: event.post_hp! }))
      if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      break

    case 'hp_regen':
      requireKnownUnit(newState, event, event.unit_id)
      // Backend MUST provide post_hp - no fallback fields
      if (event.post_hp === undefined || event.post_hp === null) {
        console.error(`⚠️ hp_regen event ${event.seq} missing required field: post_hp`)
        shouldUpdateSummary = false
        break
      }
      updateKnownUnitById(newState, event, event.unit_id, u => ({ ...u, hp: event.post_hp! }))
      // Only log significant regen amounts to avoid spam
      if ((event.amount ?? 0) >= 1) {
        if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      }
      break

    case 'damage_over_time_tick':
      requireKnownUnit(newState, event, event.unit_id)
      if (event.unit_id) {
        requireEffectId(event)
        // Backend MUST provide canonical post_hp - no alias fallback
        if (event.post_hp === undefined || event.post_hp === null) {
          console.error(`⚠️ damage_over_time_tick event ${event.seq} missing required field: post_hp`)
          shouldUpdateSummary = false
          break
        }

        const shieldAbsorbed = event.shield_absorbed ?? 0
        const hasCanonicalPostShield = event.post_shield !== undefined && event.post_shield !== null
        if (typeof shieldAbsorbed !== 'number' || !Number.isFinite(shieldAbsorbed) || shieldAbsorbed < 0) {
          console.error(`⚠️ damage_over_time_tick event ${event.seq} has invalid shield_absorbed`)
          shouldUpdateSummary = false
          break
        }
        if (hasCanonicalPostShield && (typeof event.post_shield !== 'number' || !Number.isFinite(event.post_shield))) {
          console.error(`⚠️ damage_over_time_tick event ${event.seq} has invalid canonical post_shield`)
          shouldUpdateSummary = false
          break
        }
        if (shieldAbsorbed > 0 && !hasCanonicalPostShield) {
          console.error(`⚠️ damage_over_time_tick event ${event.seq} missing required field: post_shield for shield absorption`)
          shouldUpdateSummary = false
          break
        }

        const applyDotPostState = (u: Unit) => ({
          ...u,
          hp: event.post_hp!,
          ...(hasCanonicalPostShield ? { shield: event.post_shield! } : {})
        })

        updateKnownUnitById(newState, event, event.unit_id, applyDotPostState)
      }
      if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      break

    case 'regen_gain':
      requireKnownUnit(newState, event, event.unit_id)
      if (typeof event.post_hp_regen_per_sec !== 'number' || !Number.isFinite(event.post_hp_regen_per_sec)) {
        throw new CombatReplayValidationError(event, 'missing required post_hp_regen_per_sec', event.unit_id)
      }
      if (event.unit_id) {
        const dur = event.duration || 5
        const expiresAt = ctx.simTime + dur // Use simTime for expiry
        newState.regenMap = { ...newState.regenMap, [event.unit_id]: { amount_per_sec: event.amount_per_sec || 0, total_amount: event.total_amount || 0, expiresAt } }
        updateKnownUnitById(newState, event, event.unit_id, unit => ({
          ...unit,
          buffed_stats: {
            ...(unit.buffed_stats || {}),
            hp_regen_per_sec: event.post_hp_regen_per_sec
          }
        }))
        if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      }
      break

    case 'shield_applied':
      requireKnownUnit(newState, event, event.unit_id)
      const shieldEffectId = requireEffectId(event)
      if (typeof event.amount !== 'number') {
        console.error(`⚠️ shield_applied event ${event.seq} missing required field: amount`)
        shouldUpdateSummary = false
        break
      }
      if (typeof event.post_shield !== 'number' || !Number.isFinite(event.post_shield)) {
        console.error(`⚠️ shield_applied event ${event.seq} missing required field: post_shield`)
        shouldUpdateSummary = false
        break
      }
      {
        const updateFn = (u: Unit) => {
          const effect: EffectSummary = {
            id: shieldEffectId,
            type: 'shield',
            ...itemEffectContext(event),
            amount: event.amount,
            duration: event.duration,
            caster_name: event.caster_name,
            expiresAt: event.duration ? ctx.simTime + event.duration : undefined,
            applied_amount: event.amount
          }
          // CRITICAL: Create NEW effects array to prevent shared references
          const newEffects = [...(u.effects || []), { ...effect }]
          return { ...u, effects: newEffects, shield: event.post_shield! }
        }
        updateKnownUnitById(newState, event, event.unit_id, updateFn)
      }
      if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      break

    case 'effect_applied':
      if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      requireKnownUnit(newState, event, event.unit_id)
      const appliedEffectId = requireEffectId(event)
      if (!event.effect || typeof event.effect !== 'object') {
        throw new CombatReplayValidationError(event, 'missing canonical effect object', event.unit_id)
      }
      const embeddedEffectId = requireEffectId(event, event.effect.id, 'effect.id')
      if (embeddedEffectId !== appliedEffectId) {
        throw new CombatReplayValidationError(event, 'canonical effect id does not match effect_id', event.unit_id)
      }
      if (typeof event.effect.type !== 'string' || !event.effect.type.trim()) {
        throw new CombatReplayValidationError(event, 'missing canonical effect.type', event.unit_id)
      }
      {
        const canonicalEffect: EffectSummary = {
          ...event.effect,
          ...itemEffectContext(event),
          id: appliedEffectId,
          type: event.effect.type,
          expiresAt: event.effect.expires_at,
          caster_name: event.caster_name,
        }
        const updateFn = (u: Unit) => ({
          ...u,
          effects: [...(u.effects || []), canonicalEffect],
        })
        updateKnownUnitById(newState, event, event.unit_id, updateFn)
      }
      break

    case 'shield_broken':
      requireKnownUnit(newState, event, event.unit_id)
      if (event.unit_id) {
        const clearShield = (u: Unit) => ({
          ...u,
          shield: 0,
          effects: (u.effects || []).filter(effect => effect.type !== 'shield'),
        })
        updateKnownUnitById(newState, event, event.unit_id, clearShield)
      }
      if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      break

    case 'unit_stunned':
      requireKnownUnit(newState, event, event.unit_id)
      const stunEffectId = requireEffectId(event)
      if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      if (event.unit_id) {
        const effect: EffectSummary = {
          id: stunEffectId,
          type: 'stun',
          ...itemEffectContext(event),
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
        updateKnownUnitById(newState, event, event.unit_id, updateFn)
      }
      break

    case 'damage_over_time_applied':
      if (logLine) newState.combatLog = [...newState.combatLog, logLine]
      requireKnownUnit(newState, event, event.unit_id)
      const dotEffectId = requireEffectId(event)
      if (typeof event.damage !== 'number' || !Number.isFinite(event.damage) || event.damage <= 0) {
        console.error(`⚠️ damage_over_time_applied event ${event.seq} missing canonical damage for unit ${event.unit_id}`)
        shouldUpdateSummary = false
        break
      }
      if (event.expires_at === undefined || event.expires_at === null) {
        console.error(`⚠️ damage_over_time_applied event ${event.seq} missing canonical expires_at for unit ${event.unit_id}`)
        shouldUpdateSummary = false
        break
      }
      {
        const effect: EffectSummary = {
          id: dotEffectId,
          type: 'damage_over_time',
          ...itemEffectContext(event),
          damage: event.damage,
          duration: event.duration,
          ticks: event.ticks,
          interval: event.interval,
          caster_name: event.caster_name,
          next_tick_time: event.next_tick_time,
          expires_at: event.expires_at,
          expiresAt: event.expires_at,
          source: event.source,
        }
        console.log(`[EFFECT DEBUG] Applying DoT to ${event.unit_id}:`, effect)
        const updateFn = (u: Unit) => {
          // CRITICAL: Create NEW effects array to prevent shared references
          const newEffects = [...(u.effects || []), { ...effect }]
          console.log(`[EFFECT DEBUG] ${u.id} effects before: ${u.effects?.length || 0}, after: ${newEffects.length}`)
          return { ...u, effects: newEffects }
        }
        updateKnownUnitById(newState, event, event.unit_id, updateFn)
      }
      break

    case 'damage_over_time_expired':
      requireKnownUnit(newState, event, event.unit_id)
      const dotExpiredEffectId = requireEffectId(event)
      if (event.unit_id) {
        // Backend MUST provide effect_id
        if (event.post_hp === undefined || event.post_hp === null) {
          console.error(`⚠️ damage_over_time_expired event ${event.seq} missing required field: post_hp`)
          shouldUpdateSummary = false
          break
        }

        // Remove the DoT effect by id
        const removeEffectFn = (u: Unit) => ({
          ...u,
          effects: u.effects?.filter(e => e.id !== dotExpiredEffectId) || []
        })
        updateKnownUnitById(newState, event, event.unit_id, removeEffectFn)
        updateKnownUnitById(newState, event, event.unit_id, u => ({ ...u, hp: event.post_hp! }))
      }
      break

    case 'effect_expired':
      console.log('[EFFECT_EXPIRED] Processing:', event)
      requireKnownUnit(newState, event, event.unit_id)
      const expiredEffectId = requireEffectId(event)
      if (event.unit_id) {
        // Backend MUST provide effect_id - no property matching fallback
        // Find and remove the effect, reverting its stat changes
        const removeAndRevertFn = (u: Unit) => {
          const expiredEffect = u.effects?.find(e => e.id === expiredEffectId)
          const remainingEffects = u.effects?.filter(e => e.id !== expiredEffectId) || []

          console.log('[EFFECT_EXPIRED] Found effect:', expiredEffect, 'remaining:', remainingEffects.length)

          if (!expiredEffect) {
            // Fail-fast: expiration without matching effect is a contract violation
            throw new Error(`[EFFECT_EXPIRED] Missing effect ${expiredEffectId} on unit ${u.id} at seq=${event.seq}`)
          }

          // Revert stat changes from the expired effect
          let newU = { ...u, effects: remainingEffects }

          if (expiredEffect.type === 'shield') {
            if (event.post_shield === undefined || event.post_shield === null) {
              throw new Error(`[EFFECT_EXPIRED] Missing post_shield for unit ${u.id} at seq=${event.seq}`)
            }
            newU.shield = event.post_shield
          } else if (expiredEffect.stat) {
            if (expiredEffect.applied_delta === undefined) {
              throw new Error(`[EFFECT_EXPIRED] Stat effect ${expiredEffectId} missing applied_delta for unit ${u.id} at seq=${event.seq}`)
            }
            const delta = -expiredEffect.applied_delta  // Negative to revert
            console.log('[EFFECT_EXPIRED] Reverting stat:', expiredEffect.stat, 'delta:', delta)

            if (expiredEffect.stat === 'hp') {
              if (event.post_hp === undefined || event.post_hp === null) {
                throw new Error(`[EFFECT_EXPIRED] Missing post_hp for unit ${u.id} at seq=${event.seq}`)
              }
            } else if (expiredEffect.stat === 'attack') {
              if (event.post_attack === undefined || event.post_attack === null) {
                throw new Error(`[EFFECT_EXPIRED] Missing post_attack for unit ${u.id} at seq=${event.seq}`)
              }
              newU.attack = event.post_attack
              newU.buffed_stats = { ...u.buffed_stats, attack: newU.attack }
            } else if (expiredEffect.stat === 'defense') {
              if (event.post_defense === undefined || event.post_defense === null) {
                throw new Error(`[EFFECT_EXPIRED] Missing post_defense for unit ${u.id} at seq=${event.seq}`)
              }
              newU.defense = event.post_defense
              newU.buffed_stats = { ...u.buffed_stats, defense: newU.defense }
            } else if (expiredEffect.stat === 'attack_speed') {
              if (event.post_attack_speed === undefined || event.post_attack_speed === null) {
                throw new Error(`[EFFECT_EXPIRED] Missing post_attack_speed for unit ${u.id} at seq=${event.seq}`)
              }
              newU.attack_speed = event.post_attack_speed
              newU.buffed_stats = { ...u.buffed_stats, attack_speed: newU.attack_speed }
            } else if (expiredEffect.stat === 'max_hp') {
              if (event.post_max_hp === undefined || event.post_hp === undefined || event.post_hp === null) {
                throw new Error(`[EFFECT_EXPIRED] Missing post_max_hp/post_hp for unit ${u.id} at seq=${event.seq}`)
              }
              newU.max_hp = event.post_max_hp
              newU.hp = event.post_hp
              newU.buffed_stats = { ...u.buffed_stats, hp: newU.max_hp }
            }
          }

          return newU
        }

        updateKnownUnitById(newState, event, event.unit_id, removeAndRevertFn)

        if (event.post_hp !== undefined && event.post_hp !== null) {
          updateKnownUnitById(newState, event, event.unit_id, u => ({ ...u, hp: event.post_hp! }))
        }
      }
      break

    default:
      throw new CombatReplayValidationError(event, `unsupported event type=${event.type}`)

  }

  if (shouldUpdateSummary) {
    newState.combatSummary = updateCombatSummary(newState.combatSummary ?? createCombatSummary(), event)
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
      // CRITICAL: Ensure hp is preserved if not explicitly set by updater
      // Some updaters return partial objects, so we must merge with original
      return {
        ...deepCopy,        // Start with full original unit
        ...updated,         // Apply updates
        effects: updated.effects ? [...updated.effects] : deepCopy.effects ? [...deepCopy.effects] : [],
        buffed_stats: updated.buffed_stats ? { ...updated.buffed_stats } : deepCopy.buffed_stats ? { ...deepCopy.buffed_stats } : {}
      }
    }
    return u
  })
}
