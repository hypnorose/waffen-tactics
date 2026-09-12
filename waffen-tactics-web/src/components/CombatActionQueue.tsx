import type { CombatEvent } from '../hooks/combat/types'

export interface CombatActionQueueEntry {
  index: number
  eventId: string
  label: string
  detail: string
}

interface Props {
  events: CombatEvent[]
  currentIndex: number
  limit?: number
}

const EVENT_LABELS: Record<string, string> = {
  animation_start: 'ATTACK START',
  attack: 'ATTACK',
  unit_attack: 'ATTACK',
  damage: 'REDIRECT DAMAGE',
  damage_dodged: 'DODGE',
  attack_missed: 'MISS',
  miss: 'MISS',
  multi_hit: 'MULTI-HIT',
  unit_heal: 'HEAL',
  heal: 'HEAL',
  hp_regen: 'REGEN',
  regen_gain: 'REGEN',
  shield_applied: 'SHIELD',
  shield_broken: 'SHIELD BREAK',
  effect_applied: 'EFFECT',
  effect_expired: 'EFFECT EXPIRED',
  stat_buff: 'BUFF',
  passive_triggered: 'PASSIVE',
  unit_stunned: 'STUN',
  damage_over_time_applied: 'DOT APPLIED',
  damage_over_time_tick: 'DOT TICK',
  damage_over_time_expired: 'DOT EXPIRED',
  unit_died: 'DEATH',
  unit_revived: 'REVIVE',
  revive: 'REVIVE',
  formation_changed: 'MOVE',
  skill_cast: 'SKILL',
  victory: 'VICTORY',
  defeat: 'DEFEAT',
  gold_reward: 'REWARD',
}

function eventDetail(event: CombatEvent): string {
  if (event.type === 'unit_attack' || event.type === 'damage' || event.type === 'damage_dodged' || event.type === 'animation_start') {
    const attacker = event.attacker_name || event.attacker_id
    const target = event.target_name || event.target_id
    if (attacker && target) return `${attacker} → ${target}`
    return target || attacker || 'Target pending'
  }

  return event.unit_name || event.unit_id || event.target_name || event.target_id || 'Unit pending'
}

function eventLabel(event: CombatEvent): string {
  const hasItemContext = typeof event.item_id === 'string' || typeof event.item_effect_id === 'string'
  const itemLabel = hasItemContext
    ? ({
      effect_applied: 'ITEM EFFECT',
      effect_expired: 'ITEM EXPIRED',
      stat_buff: 'ITEM BUFF',
      passive_triggered: 'ITEM PASSIVE',
    } as Record<string, string>)[event.type]
    : undefined
  const label = itemLabel || EVENT_LABELS[event.type] || event.type.replace(/_/g, ' ').toUpperCase()
  return event.bonus_attack && (event.type === 'unit_attack' || event.type === 'animation_start') ? `BONUS ${label}` : label
}

export function getCombatActionQueueEntries(events: CombatEvent[], currentIndex: number, limit = 6): CombatActionQueueEntry[] {
  if (events.length === 0 || limit <= 0) return []
  const start = Math.min(Math.max(0, currentIndex), events.length - 1)
  return events.slice(start, start + limit).map((event, offset) => ({
    index: start + offset,
    eventId: event.event_id || `${event.type}:${event.seq ?? start + offset}`,
    label: eventLabel(event),
    detail: eventDetail(event),
  }))
}

export default function CombatActionQueue({ events, currentIndex, limit = 6 }: Props) {
  const entries = getCombatActionQueueEntries(events, currentIndex, limit)
  const selectedIndex = events.length > 0 ? Math.min(Math.max(0, currentIndex), events.length - 1) : -1
  const pendingCount = selectedIndex >= 0 ? Math.max(0, events.length - selectedIndex - 1) : 0

  return (
    <details className="combat-action-queue">
      <summary>
        <span>Action queue</span>
        <span className="combat-action-queue-count">{pendingCount} pending</span>
      </summary>
      {entries.length > 0 ? (
        <ol className="combat-action-queue-list">
          {entries.map((entry) => (
            <li
              key={`${entry.eventId}:${entry.index}`}
              className={entry.index === selectedIndex ? 'is-current' : undefined}
              aria-current={entry.index === selectedIndex ? 'step' : undefined}
            >
              <span className="combat-action-queue-index">{entry.index + 1}</span>
              <span className="combat-action-queue-copy">
                <strong>{entry.label}</strong>
                <span>{entry.detail}</span>
              </span>
            </li>
          ))}
        </ol>
      ) : (
        <p className="combat-action-queue-empty">Waiting for canonical replay</p>
      )}
    </details>
  )
}
