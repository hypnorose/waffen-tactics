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

function getDotHpDamage(event: CombatEvent): number {
  const preHp = event.pre_hp
  const postHp = event.post_hp
  if (typeof preHp === 'number' && Number.isFinite(preHp) && typeof postHp === 'number' && Number.isFinite(postHp)) {
    return Math.max(0, preHp - postHp)
  }

  const incomingDamage = Math.max(0, Number(event.damage ?? event.applied_damage ?? event.amount ?? 0))
  const shieldAbsorbed = event.shield_absorbed
  if (typeof shieldAbsorbed === 'number' && Number.isFinite(shieldAbsorbed)) {
    return Math.max(0, incomingDamage - shieldAbsorbed)
  }
  return incomingDamage
}

function formatDotTickLog(event: CombatEvent): string {
  const unit = event.unit_name || event.unit_id || 'Unit'
  const incomingDamage = Math.max(0, Number(event.damage ?? event.applied_damage ?? event.amount ?? 0))
  const shieldAbsorbed = event.shield_absorbed
  if (typeof shieldAbsorbed === 'number' && Number.isFinite(shieldAbsorbed) && shieldAbsorbed > 0) {
    const hpDamage = getDotHpDamage(event)
    if (hpDamage > 0) {
      return tagDot(`${unit} -${formatAmount(hpDamage)} HP, -${formatAmount(shieldAbsorbed)} shield`)
    }
    return tagDot(`${unit} -${formatAmount(shieldAbsorbed)} shield`)
  }
  return tagDot(`${unit} -${formatAmount(incomingDamage)} HP`)
}

function tagDot(body: string): string {
  return `[DOT] ${body}`
}

function isPercentageEvent(event: CombatEvent): boolean {
  return event.is_percentage === true || event.value_type === 'percentage' || event.value_type === 'percentage_of_max'
}

function pickUnitName(event: CombatEvent): string {
  return event.attacker_name || event.caster_name || event.unit_name || event.target_name || event.message || 'Unknown'
}

function formatEventContext(
  event: CombatEvent,
  options: { includeDescription?: boolean; includeDuration?: boolean } = {}
): string {
  const parts: string[] = []
  const source = event.caster_name || event.healer_name || event.source || event.caster_id || event.source_id
  const unitName = event.unit_name || event.unit_id

  if (source && source !== unitName) parts.push(`źródło: ${source}`)
  if (event.trigger) parts.push(`trigger: ${event.trigger}`)
  const target = event.target_name || event.target_id
  if (target && target !== unitName) parts.push(`cel: ${target}`)
  if (event.target) parts.push(`typ celu: ${event.target}`)
  if (event.cause) parts.push(`powód: ${event.cause}`)
  if (event.scope) parts.push(`zakres: ${event.scope}`)
  if (event.limit !== undefined && event.limit !== null && event.limit !== '') parts.push(`limit: ${event.limit}`)
  if (options.includeDuration !== false && event.duration !== undefined && event.duration !== null) {
    parts.push(`czas: ${formatAmount(event.duration)}s`)
  }
  if (event.expires_at !== undefined && event.expires_at !== null) {
    parts.push(`wygasa: ${formatAmount(event.expires_at)}s`)
  }
  if (options.includeDescription !== false && event.description) parts.push(event.description)

  return parts.length > 0 ? ` (${parts.join(', ')})` : ''
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
      return tag('PASSIVE', `${event.unit_name || event.unit_id || 'Unit'}${event.passive_name ? ` — ${event.passive_name}` : ''}: ${event.description || event.effect || 'efekt aktywny'}${formatEventContext(event, { includeDescription: false })}`)
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
    case 'skill_cast': {
      const caster = event.caster_name || event.caster_id || event.unit_name || 'Unit'
      const skill = event.skill_name || 'umiejętność'
      const target = event.target_name || event.target_id
      const damage = event.damage ?? event.applied_damage
      const targetText = target ? ` na ${target}` : ''
      const damageText = typeof damage === 'number' && Number.isFinite(damage)
        ? ` za ${formatAmount(damage)} obrażeń`
        : ''
      return tag('SKILL', `${caster} używa ${skill}${targetText}${damageText}`)
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
      return tag(prefix, `${event.unit_name || event.unit_id || 'Unit'} ${sign}${formatAmount(Math.abs(rawAmount))}${suffix} ${stat}${duration}${formatEventContext(event, { includeDuration: false })}`)
    }
    case 'mana_update':
      // Mana remains an authoritative runtime/replay event, but continuous
      // updates are rendered in the HUD rather than as player-facing log lines.
      return null
    case 'victory':
      return tag('RESULT', 'ZWYCIESTWO')
    case 'defeat':
      return tag('RESULT', event.message || 'PRZEGRANA')
    case 'unit_heal':
    case 'heal':
      return tag('HEAL', `${event.unit_name || event.unit_id || 'Unit'} +${formatAmount(event.amount)} HP${formatEventContext(event)}`)
    case 'hp_regen':
      return tag('REGEN', `${event.unit_name || event.unit_id || 'Unit'} regeneruje +${formatAmount(event.amount)} HP`)
    case 'regen_gain':
      return tag('REGEN', `${event.unit_name || event.unit_id || 'Unit'} dostaje +${formatAmount(event.total_amount)} HP przez ${formatAmount(event.duration || 0)}s${formatEventContext(event, { includeDuration: false })}`)
    case 'shield_applied':
      return tag('SHIELD', `${event.unit_name || event.unit_id || 'Unit'} +${formatAmount(event.amount)} shield${formatEventContext(event)}`)
    case 'effect_applied':
      return tag('EFFECT', `${event.unit_name || event.unit_id || 'Unit'} gains ${event.effect_type || event.effect?.type || 'effect'}${formatEventContext(event)}`)
    case 'shield_broken':
      return tag('SHIELD BREAK', `${event.unit_name || event.unit_id || 'Unit'} traci tarczę (${formatAmount(event.amount)})`)
    case 'unit_stunned':
      return tag('STUN', `${event.unit_name || event.unit_id || 'Unit'} oszolomiony na ${formatAmount(event.duration)}s${formatEventContext(event, { includeDuration: false })}`)
    case 'damage_over_time_applied':
      return tag('DOT', `${event.unit_name || event.unit_id || 'Unit'} otrzymuje DoT (${event.ticks || '?'} ticki)${formatEventContext(event)}`)
    case 'damage_over_time_tick':
      return formatDotTickLog(event)
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
    const damage = getDotHpDamage(event)
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
