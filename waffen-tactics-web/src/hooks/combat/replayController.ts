import { applyCombatEvent } from './applyEvent'
import { computeDelayMs, normalizeCombatSpeed } from './replayTiming'
import type { CombatEvent, CombatState } from './types'

export class ReplaySeekError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ReplaySeekError'
  }
}

export type ReplaySchedule =
  | { kind: 'wait' }
  | { kind: 'complete' }
  | { kind: 'advance'; nextIndex: number; delayMs: number }

/**
 * Decides the next playback transition without React state or timers.
 * Incomplete buffers wait for transport instead of guessing a terminal state;
 * completed buffers expose completion only after the final canonical event.
 */
export function getReplaySchedule(
  events: CombatEvent[],
  currentIndex: number,
  isBufferedComplete: boolean,
  combatSpeed: number,
): ReplaySchedule {
  const currentEvent = events[currentIndex]
  if (!currentEvent) return isBufferedComplete ? { kind: 'complete' } : { kind: 'wait' }

  const nextEvent = events[currentIndex + 1]
  if (!nextEvent) return isBufferedComplete ? { kind: 'complete' } : { kind: 'wait' }

  return {
    kind: 'advance',
    nextIndex: currentIndex + 1,
    delayMs: computeDelayMs(currentEvent, nextEvent, normalizeCombatSpeed(combatSpeed), 1),
  }
}

export const createEmptyCombatState = (): CombatState => ({
  playerUnits: [],
  opponentUnits: [],
  combatLog: [],
  isFinished: false,
  victory: null,
  finalState: null,
  synergies: {},
  traits: [],
  opponentInfo: null,
  regenMap: {},
  simTime: 0,
  defeatMessage: undefined,
  combatSummary: undefined,
  activeAnimations: [],
  appliedFormationEvents: {},
  appliedDamageDodgedEvents: {},
  appliedShieldBrokenEvents: {},
  appliedReviveEvents: {},
})

function cloneInitialState(state: CombatState): CombatState {
  return {
    ...state,
    playerUnits: state.playerUnits.map(unit => ({ ...unit, effects: unit.effects ? [...unit.effects] : unit.effects })),
    opponentUnits: state.opponentUnits.map(unit => ({ ...unit, effects: unit.effects ? [...unit.effects] : unit.effects })),
    combatLog: [...state.combatLog],
    synergies: { ...state.synergies },
    traits: [...state.traits],
    regenMap: { ...state.regenMap },
    activeAnimations: [],
    appliedFormationEvents: { ...state.appliedFormationEvents },
    appliedDamageDodgedEvents: { ...state.appliedDamageDodgedEvents },
    appliedShieldBrokenEvents: { ...state.appliedShieldBrokenEvents },
    appliedReviveEvents: { ...state.appliedReviveEvents },
  }
}

export function validateReplayIndex(events: CombatEvent[], index: number): number {
  if (!Number.isInteger(index)) {
    throw new ReplaySeekError('Pozycja replayu musi być liczbą całkowitą.')
  }
  if (index < -1 || index >= events.length) {
    throw new ReplaySeekError(`Pozycja replayu ${index} jest poza zakresem 0–${Math.max(0, events.length - 1)}.`)
  }
  return index
}

/**
 * Rebuilds the state at an event index from the canonical stream.
 * A seek never trusts the currently displayed state, so backward and forward
 * seeks use exactly the same reducer path as a fresh replay.
 */
export function reconstructCombatState(
  events: CombatEvent[],
  index: number,
  initialState: CombatState = createEmptyCombatState(),
): CombatState {
  const targetIndex = validateReplayIndex(events, index)
  let state = cloneInitialState(initialState)

  for (let eventIndex = 0; eventIndex <= targetIndex; eventIndex += 1) {
    const event = events[eventIndex]
    // Animation events are transient presentation, not authoritative state.
    // Replaying them during a seek would create nondeterministic Date.now IDs
    // and stale projectiles while the user inspects a historical state.
    if (event.type === 'animation_start') continue
    state = applyCombatEvent(state, event, { simTime: state.simTime })
  }

  state.activeAnimations = []
  return state
}
