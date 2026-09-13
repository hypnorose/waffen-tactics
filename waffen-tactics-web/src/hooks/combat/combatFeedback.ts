import type { CombatEvent } from './types'

export type CombatFeedbackTone = 'damage' | 'heal' | 'effect' | 'death' | 'neutral'

export interface CombatFeedback {
  id: string
  targetId: string
  text: string
  tone: CombatFeedbackTone
}

function finiteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function formatAmount(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
}

function eventKey(event: CombatEvent): string {
  return event.event_id || `${event.type}:${event.seq ?? 'unknown'}`
}

function feedback(event: CombatEvent, targetId: unknown, text: string, tone: CombatFeedbackTone, role: string): CombatFeedback[] {
  if (typeof targetId !== 'string' || targetId.trim() === '' || text.trim() === '') return []
  return [{
    id: `combat-feedback:${eventKey(event)}:${role}`,
    targetId,
    text,
    tone,
  }]
}

function authoritativeDelta(event: CombatEvent, beforeKey: keyof CombatEvent, afterKey: keyof CombatEvent): number | null {
  const before = finiteNumber(event[beforeKey])
  const after = finiteNumber(event[afterKey])
  return before !== null && after !== null ? after - before : null
}

function damageFeedback(event: CombatEvent, targetId: unknown): CombatFeedback[] {
  if (event.dodged) return feedback(event, targetId, 'DODGE', 'neutral', 'dodge')

  const hpBefore = finiteNumber(event.pre_hp)
  const hpAfter = finiteNumber(event.post_hp ?? event.target_hp ?? event.new_hp)
  const hasAuthoritativeHp = hpBefore !== null && hpAfter !== null
  const hpLoss = hasAuthoritativeHp
    ? Math.max(0, hpBefore - hpAfter)
    : Math.max(0, finiteNumber(event.applied_damage) ?? finiteNumber(event.damage) ?? 0)
  const shieldLoss = Math.max(0, finiteNumber(event.shield_absorbed) ?? 0)
  const prefix = event.bonus_attack ? 'BONUS ' : ''
  const entries: CombatFeedback[] = []

  if (hpLoss > 0) {
    entries.push(...feedback(event, targetId, `${prefix}-${formatAmount(hpLoss)} HP`, 'damage', 'damage'))
  } else if (event.bonus_attack && shieldLoss === 0 && !hasAuthoritativeHp) {
    entries.push(...feedback(event, targetId, 'BONUS HIT', 'neutral', 'bonus'))
  }
  if (shieldLoss > 0) {
    entries.push(...feedback(event, targetId, `-${formatAmount(shieldLoss)} SHIELD`, 'damage', 'shield'))
  }

  return entries
}

function multiHitFeedback(event: CombatEvent): CombatFeedback[] {
  const targetIds = Array.isArray(event.target_ids)
    ? event.target_ids.filter((targetId): targetId is string => typeof targetId === 'string' && targetId.trim() !== '')
    : []

  return targetIds.flatMap((targetId, targetIndex) => damageFeedback(event, targetId).map((entry) => ({
    ...entry,
    id: `${entry.id}:multi-hit:${targetIndex}:${targetId}`,
    text: `MULTI-HIT ${entry.text}`,
  })))
}

function healFeedback(event: CombatEvent): CombatFeedback[] {
  const actualGain = authoritativeDelta(event, 'pre_hp', 'post_hp')
  const amount = actualGain !== null
    ? Math.max(0, actualGain)
    : Math.max(0, finiteNumber(event.amount) ?? finiteNumber(event.total_amount) ?? 0)
  if (amount <= 0) return []
  return feedback(event, event.unit_id, `+${formatAmount(amount)} HP`, 'heal', 'heal')
}

function effectMarker(event: CombatEvent, sign: '+' | '-'): string {
  const isItem = typeof event.item_id === 'string' || typeof event.item_effect_id === 'string'
  return `${sign}${isItem ? 'ITEM' : 'EFFECT'}`
}

export function getCombatFeedback(event: CombatEvent | undefined): CombatFeedback[] {
  if (!event || typeof event.type !== 'string') return []

  switch (event.type) {
    case 'unit_attack':
    case 'damage':
      return damageFeedback(event, event.target_id)
    case 'attack':
      return damageFeedback(event, event.target_id)
    case 'multi_hit':
      return multiHitFeedback(event)
    case 'damage_over_time_tick':
      return damageFeedback(event, event.unit_id)
    case 'damage_dodged':
    case 'attack_missed':
    case 'miss':
      return feedback(event, event.target_id, event.type === 'damage_dodged' ? 'DODGE' : 'MISS', 'neutral', 'outcome')
    case 'unit_heal':
    case 'heal':
      if (event.cause === 'set2_revive') {
        return feedback(event, event.unit_id, 'REVIVE', 'heal', 'revive')
      }
      return healFeedback(event)
    case 'hp_regen':
    case 'regen_gain':
      return healFeedback(event)
    case 'shield_applied': {
      const amount = Math.max(0, finiteNumber(event.amount) ?? finiteNumber(event.applied_amount) ?? 0)
      return amount > 0 ? feedback(event, event.unit_id, `+${formatAmount(amount)} SHIELD`, 'heal', 'shield') : []
    }
    case 'shield_broken': {
      const amount = Math.max(0, finiteNumber(event.amount) ?? 0)
      return feedback(event, event.unit_id, amount > 0 ? `-${formatAmount(amount)} SHIELD` : 'SHIELD BREAK', 'damage', 'shield-break')
    }
    case 'stat_buff': {
      const delta = finiteNumber(event.applied_delta) ?? finiteNumber(event.amount) ?? finiteNumber(event.value)
      const sign = delta !== null && delta < 0 ? '-' : '+'
      const marker = delta !== null && delta < 0 ? 'DEBUFF' : 'BUFF'
      const stat = typeof event.stat === 'string' && event.stat.trim() ? ` ${event.stat.replace(/_/g, ' ').toUpperCase()}` : ''
      return feedback(event, event.unit_id, `${sign}${marker}${stat}`, 'effect', 'stat')
    }
    case 'effect_applied':
      return feedback(event, event.unit_id, effectMarker(event, '+'), 'effect', 'effect')
    case 'effect_expired':
      return feedback(event, event.unit_id, effectMarker(event, '-'), 'effect', 'effect-expired')
    case 'passive_triggered':
      return feedback(event, event.unit_id, typeof event.item_id === 'string' ? '+ITEM' : '+PASSIVE', 'effect', 'passive')
    case 'unit_stunned':
      return feedback(event, event.unit_id, '+STUN', 'effect', 'stun')
    case 'unit_died':
      return feedback(event, event.unit_id, 'DEFEATED', 'death', 'death')
    case 'unit_revived':
    case 'revive':
      return feedback(event, event.unit_id, 'REVIVE', 'heal', 'revive')
    case 'formation_changed':
      return feedback(event, event.unit_id, 'MOVE', 'neutral', 'formation')
    default:
      return []
  }
}
