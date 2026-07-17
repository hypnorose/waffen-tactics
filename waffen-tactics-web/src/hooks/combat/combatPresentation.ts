import { CombatEvent, CombatSummary, CombatSummaryEntry, CombatSummaryFocus, CombatUnitRoundStats } from './types'

export function createCombatSummary(): CombatSummary {
  return {
    totalDamageByUnit: {},
    unitStatsByUnit: {},
    bonusAttacks: 0,
    firstDeath: null,
    lastAction: null,
    focus: null,
    roundResult: null,
  }
}

function getEventTimestamp(event: CombatEvent): number | undefined {
  return typeof event.timestamp === 'number' && Number.isFinite(event.timestamp)
    ? event.timestamp
    : undefined
}

function ensureUnitStats(summary: CombatSummary, unitId: string, unitName?: string): CombatUnitRoundStats {
  const existing = summary.unitStatsByUnit[unitId]
  if (existing) {
    if (unitName && (!existing.unit_name || existing.unit_name === 'Unknown')) {
      existing.unit_name = unitName
    }
    return existing
  }

  const created: CombatUnitRoundStats = {
    unit_name: unitName || 'Unknown',
    damage_dealt: 0,
    damage_received: 0,
    avg_dps: 0,
    avg_damage_received: 0,
    active_seconds: 0,
    participated: true,
  }
  summary.unitStatsByUnit[unitId] = created
  return created
}

function markActivity(summary: CombatSummary, unitId: string | undefined, unitName?: string, timestamp?: number) {
  if (!unitId) return
  const stats = ensureUnitStats(summary, unitId, unitName)
  if (timestamp !== undefined && stats.first_activity_at === undefined) {
    stats.first_activity_at = timestamp
  }
}

function recalculateUnitAverages(summary: CombatSummary) {
  const fallbackEnd = summary.roundEndAt ?? summary.lastEventAt ?? summary.roundStartAt
  if (fallbackEnd === undefined) return

  Object.values(summary.unitStatsByUnit).forEach((stats) => {
    if (stats.first_activity_at === undefined) return
    const end = stats.death_at ?? fallbackEnd
    const activeSeconds = Math.max(0.1, end - stats.first_activity_at)
    stats.active_seconds = activeSeconds
    stats.avg_dps = stats.damage_dealt / activeSeconds
    stats.avg_damage_received = stats.damage_received / activeSeconds
  })
}

function formatAmount(value?: number): string {
  if (typeof value !== 'number' || Number.isNaN(value)) return '0'
  return Number.isInteger(value) ? `${value}` : value.toFixed(2)
}

function isPercentageEvent(event: CombatEvent): boolean {
  return event.is_percentage === true || event.value_type === 'percentage' || event.value_type === 'percentage_of_max'
}

function pickUnitName(event: CombatEvent): string {
  return event.attacker_name || event.caster_name || event.unit_name || event.target_name || event.message || 'Unknown'
}

function buildSummaryFocus(event: CombatEvent): CombatSummaryFocus | null {
  if (event.type !== 'unit_attack' && event.type !== 'animation_start') return null
  return {
    attacker_id: event.attacker_id,
    attacker_name: event.attacker_name,
    target_id: event.target_id,
    target_name: event.target_name,
    bonus_attack: !!event.bonus_attack,
    timestamp: event.timestamp,
    seq: event.seq,
  }
}

export function formatCombatLogEntry(event: CombatEvent): string | null {
  const tag = (messageTag: string, body: string) => `[${messageTag}] ${body}`

  switch (event.type) {
    case 'start':
      return tag('START', 'Walka rozpoczyna sie')
    case 'animation_start':
      return null
    case 'passive_triggered':
      return tag('PASSIVE', `${event.unit_name || event.unit_id || 'Unit'}: ${event.description || event.effect || 'efekt aktywny'}`)
    case 'unit_attack': {
      const prefix = event.bonus_attack ? 'BONUS' : 'ATK'
      const damage = formatAmount(event.damage ?? event.applied_damage)
      const attacker = event.attacker_name || event.attacker_id || 'Unknown'
      const target = event.target_name || event.target_id || 'Unknown'
      const mana = typeof event.attacker_current_mana === 'number' && typeof event.attacker_max_mana === 'number'
        ? ` mana ${event.attacker_current_mana}/${event.attacker_max_mana}`
        : ''
      return tag(prefix, `${attacker} -> ${target} za ${damage}${mana}`)
    }
    case 'unit_died':
      return tag('DEATH', `${event.unit_name || event.unit_id || 'Unit'} pada`)
    case 'gold_reward':
      return tag('GOLD', `${event.unit_name || event.unit_id || 'Unit'} dostaje +${formatAmount(event.amount)} gold`)
    case 'stat_buff': {
      const rawAmount = Number(event.amount ?? event.value ?? 0)
      const isDebuff = event.buff_type === 'debuff' || rawAmount < 0
      const prefix = isDebuff ? 'DEBUFF' : 'BUFF'
      const sign = isDebuff ? '-' : '+'
      const stat = event.stat || 'stat'
      const duration = event.duration ? ` for ${formatAmount(event.duration)}s` : ''
      const suffix = isPercentageEvent(event) ? '%' : ''
      return tag(prefix, `${event.unit_name || event.unit_id || 'Unit'} ${sign}${formatAmount(Math.abs(rawAmount))}${suffix} ${stat}${duration}`)
    }
    case 'mana_update':
      return tag('MANA', `${event.unit_name || event.unit_id || 'Unit'} ${event.current_mana ?? 0}/${event.max_mana ?? 0}`)
    case 'victory':
      return tag('RESULT', 'ZWYCIESTWO')
    case 'defeat':
      return tag('RESULT', event.message || 'PRZEGRANA')
    case 'unit_heal':
    case 'heal':
      return tag('HEAL', `${event.unit_name || event.unit_id || 'Unit'} +${formatAmount(event.amount)} HP`)
    case 'hp_regen':
      return tag('REGEN', `${event.unit_name || event.unit_id || 'Unit'} regeneruje +${formatAmount(event.amount)} HP`)
    case 'regen_gain':
      return tag('REGEN', `${event.unit_name || event.unit_id || 'Unit'} dostaje +${formatAmount(event.total_amount)} HP przez ${formatAmount(event.duration || 0)}s`)
    case 'shield_applied':
      return tag('SHIELD', `${event.unit_name || event.unit_id || 'Unit'} +${formatAmount(event.amount)} shield`)
    case 'unit_stunned':
      return tag('STUN', `${event.unit_name || event.unit_id || 'Unit'} oszolomiony na ${formatAmount(event.duration)}s`)
    case 'damage_over_time_applied':
      return tag('DOT', `${event.unit_name || event.unit_id || 'Unit'} otrzymuje DoT (${event.ticks || '?'} ticki)`)
    case 'damage_over_time_tick':
      return tag('DOT', `${event.unit_name || event.unit_id || 'Unit'} -${formatAmount(event.damage)} HP`)
    case 'damage_over_time_expired':
      return tag('DOT', `${event.unit_name || event.unit_id || 'Unit'} DoT wygasl`)
    case 'effect_expired':
      return tag('BUFF', `${event.unit_name || event.unit_id || 'Unit'} efekt wygasl`)
    default:
      return null
  }
}

export function updateCombatSummary(summary: CombatSummary, event: CombatEvent): CombatSummary {
  const next: CombatSummary = {
    ...summary,
    totalDamageByUnit: { ...summary.totalDamageByUnit },
    unitStatsByUnit: Object.fromEntries(
      Object.entries(summary.unitStatsByUnit).map(([id, stats]) => [id, { ...stats }])
    ),
    focus: summary.focus,
    lastAction: summary.lastAction,
  }

  const eventTimestamp = getEventTimestamp(event)
  if (eventTimestamp !== undefined) {
    next.lastEventAt = eventTimestamp
    if (next.roundStartAt === undefined) next.roundStartAt = eventTimestamp
  }

  const logText = formatCombatLogEntry(event)
  if (logText) {
    next.lastAction = {
      type: event.type,
      text: logText,
      seq: event.seq,
      timestamp: event.timestamp,
    }
  }

  if (event.type === 'animation_start') {
    next.focus = buildSummaryFocus(event)
  }

  if (event.type === 'unit_attack') {
    const damage = Math.max(0, Number(event.applied_damage ?? event.damage ?? 0))
    const attackerId = event.attacker_id || event.caster_id || event.unit_id
    const targetId = event.target_id || event.unit_id

    markActivity(next, attackerId, event.attacker_name, eventTimestamp)
    markActivity(next, targetId, event.target_name, eventTimestamp)

    if (attackerId && damage > 0) {
      const existing = next.totalDamageByUnit[attackerId] || { unit_name: pickUnitName(event), damage: 0 }
      next.totalDamageByUnit[attackerId] = {
        unit_name: event.attacker_name || existing.unit_name,
        damage: existing.damage + damage,
      }
      const attackerStats = ensureUnitStats(next, attackerId, event.attacker_name)
      attackerStats.damage_dealt += damage
    }

    if (targetId && damage > 0) {
      const targetStats = ensureUnitStats(next, targetId, event.target_name)
      targetStats.damage_received += damage
    }
    if (event.bonus_attack) {
      next.bonusAttacks += 1
    }
    next.focus = buildSummaryFocus(event)
  }

  if (event.type === 'unit_died' && !next.firstDeath) {
    next.firstDeath = {
      unit_id: event.unit_id,
      unit_name: event.unit_name,
      timestamp: event.timestamp,
      seq: event.seq,
    }
  }

  if (event.type === 'unit_died' && event.unit_id) {
    const stats = ensureUnitStats(next, event.unit_id, event.unit_name)
    if (eventTimestamp !== undefined) stats.death_at = eventTimestamp
    markActivity(next, event.unit_id, event.unit_name, eventTimestamp)
  }

  if (event.type === 'damage_over_time_tick' && event.unit_id) {
    const damage = Math.max(0, Number(event.damage ?? event.amount ?? 0))
    markActivity(next, event.unit_id, event.unit_name, eventTimestamp)
    ensureUnitStats(next, event.unit_id, event.unit_name).damage_received += damage
  }

  if (event.type === 'victory' || event.type === 'defeat') {
    next.roundResult = logText
    next.focus = null
    if (eventTimestamp !== undefined) next.roundEndAt = eventTimestamp
  }

  if (event.type === 'end' && eventTimestamp !== undefined) next.roundEndAt = eventTimestamp

  recalculateUnitAverages(next)

  return next
}

export function getTopDamageDealer(summary: CombatSummary): CombatSummaryEntry | null {
  const entries = Object.entries(summary.totalDamageByUnit)
  if (entries.length === 0) return null

  const [unit_id, payload] = entries.sort((a, b) => b[1].damage - a[1].damage)[0]
  return {
    unit_id,
    unit_name: payload.unit_name,
    damage: payload.damage,
  }
}
