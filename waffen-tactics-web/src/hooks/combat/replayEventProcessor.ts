import { applyCombatEvent, CombatReplayValidationError } from './applyEvent'
import { compareCombatStates } from './desync'
import { CombatSnapshotValidationError } from './snapshotContract'
import type { CombatEvent, CombatState, DesyncEntry } from './types'

export interface GoldBreakdown {
  base: number
  interest: number
  milestone: number
  win_bonus: number
  total: number
  item_parts: string[]
}

export interface ReplayEventProcessInput {
  currentState: CombatState
  event: CombatEvent
  pendingEvents: CombatEvent[]
}

export interface ReplayEventProcessResult {
  state?: CombatState
  desyncs: DesyncEntry[]
  goldBreakdown?: GoldBreakdown
  shouldStop: boolean
  validationError?: CombatReplayValidationError
}

function eventUnitId(event: CombatEvent, errorUnitId?: string): string {
  return errorUnitId || event.unit_id || event.target_id || event.attacker_id || ''
}

function desyncForEvent(
  event: CombatEvent,
  pendingEvents: CombatEvent[],
  diff: Record<string, { ui: unknown, server: unknown }>,
  note: string,
  unitId = eventUnitId(event),
): DesyncEntry {
  return {
    unit_id: unitId,
    unit_name: event.unit_name || '',
    seq: event.seq,
    event_id: event.event_id,
    timestamp: event.timestamp,
    diff,
    pending_events: pendingEvents,
    note,
  }
}

function unitForId(state: CombatState, unitId: string) {
  return [...state.playerUnits, ...state.opponentUnits].find(unit => unit.id === unitId)
}

function unexpectedHpRestoration(state: CombatState, nextState: CombatState, event: CombatEvent): DesyncEntry | null {
  const relevantId = event.unit_id || event.target_id
  if (!relevantId) return null

  const oldUnit = unitForId(state, relevantId)
  const newUnit = unitForId(nextState, relevantId)
  const oldHp = oldUnit?.hp
  const newHp = newUnit?.hp
  const healTypes = new Set(['heal', 'unit_heal', 'unit_revived', 'hp_regen', 'regen_gain'])

  if (
    (oldHp === 0 || oldHp === null || oldHp === undefined) &&
    typeof newHp === 'number' &&
    newHp > 0 &&
    !healTypes.has(event.type)
  ) {
    return desyncForEvent(
      event,
      [],
      { hp: { ui: oldHp, server: newHp } },
      `hp guard: ${event.type}`,
      relevantId,
    )
  }

  return null
}

function goldBreakdownFromEvent(event: CombatEvent): GoldBreakdown | undefined {
  if (event.type !== 'gold_income') return undefined

  return {
    base: event.base || 0,
    interest: event.interest || 0,
    milestone: event.milestone || 0,
    win_bonus: event.win_bonus || 0,
    total: event.total || 0,
    item_parts: Array.isArray(event.item_parts) ? event.item_parts : [],
  }
}

export function processReplayEvent({ currentState, event, pendingEvents }: ReplayEventProcessInput): ReplayEventProcessResult {
  const goldBreakdown = goldBreakdownFromEvent(event)
  let nextState: CombatState

  try {
    nextState = applyCombatEvent(currentState, event, { simTime: currentState.simTime })
  } catch (error) {
    if (!(error instanceof CombatReplayValidationError)) throw error

    return {
      desyncs: [
        desyncForEvent(
          event,
          pendingEvents,
          { replay: { ui: 'not_applied', server: error.message } },
          `replay validation failed: ${error.message}`,
          eventUnitId(event, error.unitId),
        ),
      ],
      goldBreakdown,
      shouldStop: true,
      validationError: error,
    }
  }

  const desyncs: DesyncEntry[] = []
  let shouldStop = false
  const hpDesync = unexpectedHpRestoration(currentState, nextState, event)
  if (hpDesync) desyncs.push(hpDesync)

  if (event.game_state) {
    try {
      const snapshotDesyncs = compareCombatStates(nextState, event.game_state, event)
      desyncs.push(...snapshotDesyncs)
      shouldStop = snapshotDesyncs.length > 0
    } catch (error) {
      if (!(error instanceof CombatSnapshotValidationError)) throw error

      shouldStop = true
      desyncs.push(
        desyncForEvent(
          event,
          pendingEvents,
          { snapshot: { ui: 'not_compared', server: error.message } },
          `combat snapshot validation failed: ${error.message}`,
        ),
      )
    }
  }

  return {
    state: nextState,
    desyncs,
    goldBreakdown,
    shouldStop,
  }
}
