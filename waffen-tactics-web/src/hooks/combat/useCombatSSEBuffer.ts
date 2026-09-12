import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../../services/apiBaseUrl'
import { createIdempotencyKey } from '../../services/requestIdentity'
import { CombatEvent, CombatTransportError } from './types'
import { validateCombatEventSnapshot } from './snapshotContract'

export type CombatSSEFrameClassification =
  | { kind: 'event', event: CombatEvent }
  | { kind: 'error', error: CombatTransportError }

const FALLBACK_COMBAT_ERROR_MESSAGE = 'Nie udało się uruchomić walki. Odśwież stronę i spróbuj ponownie.'
const CONTROL_EVENT_TYPES = new Set(['units_init', 'start', 'victory', 'defeat', 'gold_income', 'end'])

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function stableSerialize(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(stableSerialize).join(',')}]`
  }
  if (isRecord(value)) {
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stableSerialize(value[key])}`).join(',')}}`
  }
  return JSON.stringify(value) ?? String(value)
}

export function classifyCombatSSEFrame(data: unknown): CombatSSEFrameClassification | null {
  if (!isRecord(data) || typeof data.type !== 'string' || !data.type.trim()) {
    return null
  }

  if (data.type === 'error') {
    const code = isNonEmptyString(data.code) ? data.code.trim() : 'combat_request_failed'
    const message = isNonEmptyString(data.message) ? data.message : FALLBACK_COMBAT_ERROR_MESSAGE
    const retriable = typeof data.retriable === 'boolean' ? data.retriable : true

    return {
      kind: 'error',
      error: { type: 'error', code, message, retriable },
    }
  }

  return { kind: 'event', event: data as unknown as CombatEvent }
}

type SharedSSESnapshot = {
  bufferedEvents: CombatEvent[]
  isBufferedComplete: boolean
  combatError: CombatTransportError | null
}

type SharedSSEState = {
  eventSource: any // Not actually EventSource; retained for compatibility.
  ingest: CombatEvent[]
  bufferedEvents: CombatEvent[]
  isBufferedComplete: boolean
  combatError: CombatTransportError | null
  stopped: boolean
  ended: boolean
  terminalOutcomeSeen: boolean
  lastEventSequence?: number
  lastSequencedEvent?: number
  frameIndex: number
  reader?: ReadableStreamDefaultReader<Uint8Array>
  listeners: Set<(state: SharedSSESnapshot) => void>
  seenFrameSignatures: Map<string, string>
  creatingPromise?: Promise<SharedSSEState>
  endTime?: number
}

function createSharedState(): SharedSSEState {
  return {
    eventSource: null,
    ingest: [],
    bufferedEvents: [],
    isBufferedComplete: false,
    combatError: null,
    stopped: false,
    ended: false,
    terminalOutcomeSeen: false,
    frameIndex: 0,
    listeners: new Set(),
    seenFrameSignatures: new Map(),
  }
}

function errorFromException(error: unknown, fallback = FALLBACK_COMBAT_ERROR_MESSAGE): CombatTransportError {
  const detail = error instanceof Error && error.message.trim() ? `: ${error.message.trim()}` : ''
  return {
    type: 'error',
    code: 'combat_stream_failed',
    message: `${fallback}${detail}`,
    retriable: true,
  }
}

async function errorFromHttpResponse(response: Response): Promise<CombatTransportError> {
  let payload: unknown = null
  try {
    const candidate = response as Response & { clone?: () => Response }
    if (typeof candidate.clone === 'function') {
      payload = await candidate.clone().json()
    } else if (typeof (response as Response & { json?: () => Promise<unknown> }).json === 'function') {
      payload = await (response as Response & { json: () => Promise<unknown> }).json()
    }
  } catch {
    payload = null
  }

  const payloadRecord = isRecord(payload) ? payload : null
  const code = isNonEmptyString(payloadRecord?.code)
    ? payloadRecord.code.trim()
    : `combat_http_${response.status}`
  const payloadMessage = payloadRecord?.message ?? payloadRecord?.error
  const message = isNonEmptyString(payloadMessage)
    ? payloadMessage
    : `Combat request failed (HTTP ${response.status}).`

  return {
    type: 'error',
    code,
    message,
    retriable: response.status >= 500 || response.status === 408 || response.status === 429,
  }
}

function protocolError(
  state: SharedSSEState,
  code: string,
  message: string,
  event?: CombatEvent,
): CombatTransportError {
  return {
    type: 'error',
    code,
    message: `${message} (frame=${state.frameIndex}, seq=${event?.seq ?? state.lastSequencedEvent ?? 'unknown'}${event?.event_id ? `, event_id=${event.event_id}` : ''})`,
    retriable: true,
    seq: event?.seq ?? state.lastEventSequence ?? state.lastSequencedEvent ?? null,
    event_id: isNonEmptyString(event?.event_id) ? event.event_id : undefined,
    frame_index: state.frameIndex,
  }
}

function validateAndRegisterEvent(state: SharedSSEState, event: CombatEvent): boolean {
  try {
    validateCombatEventSnapshot(event as unknown as Record<string, unknown>)
  } catch (error) {
    throw protocolError(
      state,
      'combat_invalid_snapshot',
      error instanceof Error ? error.message : 'Combat event contains an invalid state snapshot.',
      event,
    )
  }

  if (!Number.isInteger(event.seq) || event.seq! < 0) {
    throw protocolError(state, 'combat_invalid_sequence', 'Combat event requires a non-negative integer seq.', event)
  }

  if (event.event_id !== undefined && !isNonEmptyString(event.event_id)) {
    throw protocolError(state, 'combat_invalid_event_id', 'Combat event event_id must be a non-empty string.', event)
  }

  if (!CONTROL_EVENT_TYPES.has(event.type) && !isNonEmptyString(event.event_id)) {
    throw protocolError(state, 'combat_missing_event_id', 'Combat event is missing its canonical event_id.', event)
  }

  const identity = isNonEmptyString(event.event_id)
    ? `event_id:${event.event_id}`
    : `type_seq:${event.type}:${event.seq}`
  const signature = stableSerialize(event)
  const previousSignature = state.seenFrameSignatures.get(identity)
  if (previousSignature !== undefined) {
    if (previousSignature !== signature) {
      throw protocolError(state, 'combat_conflicting_duplicate', `Conflicting duplicate frame for ${identity}.`, event)
    }
    return false
  }
  state.seenFrameSignatures.set(identity, signature)
  state.lastEventSequence = event.seq

  if (state.ended) {
    throw protocolError(state, 'combat_event_after_end', 'Combat stream delivered an event after the terminal end frame.', event)
  }

  if (event.type === 'end') {
    state.ended = true
    state.isBufferedComplete = true
    state.endTime = Date.now()
    return true
  }

  if (event.type === 'victory' || event.type === 'defeat') {
    state.terminalOutcomeSeen = true
    return true
  }

  if (CONTROL_EVENT_TYPES.has(event.type)) {
    return true
  }

  const seq = event.seq!
  if (seq < 1) {
    throw protocolError(state, 'combat_invalid_sequence', 'Combat event sequence must start at 1 after control frames.', event)
  }
  if (state.lastSequencedEvent === undefined) {
    if (seq !== 1) {
      throw protocolError(state, 'combat_sequence_gap', 'Combat event sequence starts with a gap.', event)
    }
  } else if (seq !== state.lastSequencedEvent + 1) {
    throw protocolError(
      state,
      'combat_sequence_gap',
      `Combat event sequence is discontinuous; expected ${state.lastSequencedEvent + 1}.`,
      event,
    )
  }
  state.lastSequencedEvent = seq
  return true
}

// Persist shared state across HMR in development. Reusing an active state
// prevents a remount/reconnect from issuing a second combat request or
// replaying the same committed frames twice.
if (!(window as any).__combatSSEMap) {
  (window as any).__combatSSEMap = new Map()
}
const sseMap: Map<string, SharedSSEState> = (window as any).__combatSSEMap

function ensureSharedSSE(token: string): Promise<SharedSSEState> {
  if (!token) return Promise.reject(new Error('No token'))

  const existing = sseMap.get(token)
  if (existing) {
    if (existing.creatingPromise) return existing.creatingPromise
    if (existing.eventSource && !existing.stopped && !existing.ended) return Promise.resolve(existing)
    sseMap.delete(token)
  }

  const placeholder = createSharedState()
  sseMap.set(token, placeholder)
  const idempotencyKey = createIdempotencyKey('combat')

  const notify = (state: SharedSSEState) => {
    const snapshot: SharedSSESnapshot = {
      bufferedEvents: [...state.bufferedEvents],
      isBufferedComplete: state.isBufferedComplete,
      combatError: state.combatError,
    }
    state.listeners.forEach(listener => listener(snapshot))
  }

  const stopWithError = (state: SharedSSEState, error: CombatTransportError) => {
    if (state.combatError) return
    state.combatError = error
    state.stopped = true
    state.eventSource = null
    void state.reader?.cancel().catch(() => undefined)
    notify(state)
  }

  const creatingPromise = fetch(`${API_BASE_URL}/game/combat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({ token, idempotency_key: idempotencyKey }),
  }).then(async response => {
    if (!response.ok) {
      stopWithError(placeholder, await errorFromHttpResponse(response))
      return placeholder
    }
    if (!response.body) {
      stopWithError(placeholder, errorFromException(new Error('No response body'), 'Combat response has no stream body.'))
      return placeholder
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    const state: SharedSSEState = {
      ...createSharedState(),
      eventSource: {},
      reader,
    }
    sseMap.set(token, state)

    const processFrame = (frame: string) => {
      if (state.stopped) return
      state.frameIndex += 1
      const lines = frame.split('\n')
      const dataLines = lines
        .filter(line => line.startsWith('data:'))
        .map(line => line.slice(5).replace(/^ /, ''))
      const meaningfulLines = lines.filter(line => line.trim() && !line.startsWith(':'))

      // SSE comments and standard metadata lines are harmless. Any other
      // non-data content is a malformed frame, not a frame to ignore.
      const hasUnsupportedContent = meaningfulLines.some(line => (
        !line.startsWith('data:') &&
        !line.startsWith('event:') &&
        !line.startsWith('id:') &&
        !line.startsWith('retry:')
      ))
      if (hasUnsupportedContent || dataLines.length === 0) {
        if (hasUnsupportedContent) {
          stopWithError(state, protocolError(state, 'combat_malformed_frame', 'Combat SSE frame contains unsupported content.'))
        }
        return
      }

      let rawData: unknown
      try {
        rawData = JSON.parse(dataLines.join('\n'))
      } catch {
        stopWithError(state, protocolError(state, 'combat_malformed_frame', 'Combat SSE frame is not valid JSON.'))
        return
      }

      const classification = classifyCombatSSEFrame(rawData)
      if (!classification) {
        stopWithError(state, protocolError(state, 'combat_malformed_frame', 'Combat SSE frame is missing a valid event type.'))
        return
      }
      if (classification.kind === 'error') {
        stopWithError(state, classification.error)
        return
      }

      try {
        if (!validateAndRegisterEvent(state, classification.event)) return
      } catch (error) {
        stopWithError(
          state,
          error && typeof error === 'object' && 'type' in error && (error as { type?: unknown }).type === 'error'
            ? error as CombatTransportError
            : protocolError(state, 'combat_protocol_error', error instanceof Error ? error.message : 'Invalid combat SSE event.', classification.event),
        )
        return
      }

      state.ingest.push(classification.event)
      state.bufferedEvents = [...state.ingest]
      state.eventSource = state.ended ? null : {}
      notify(state)
    }

    const processChunk = (chunk: string) => {
      if (state.stopped) return
      buffer += chunk.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
      const frames = buffer.split('\n\n')
      buffer = frames.pop() || ''
      frames.forEach(processFrame)
    }

    const finishStream = () => {
      if (state.stopped) return
      if (buffer.trim()) {
        stopWithError(state, protocolError(state, 'combat_incomplete_frame', 'Combat SSE stream ended with an incomplete frame.'))
        return
      }
      if (!state.isBufferedComplete) {
        stopWithError(state, protocolError(state, 'combat_stream_eof', 'Combat SSE stream ended before the terminal end frame.'))
      }
    }

    const readStream = async () => {
      try {
        while (!state.stopped) {
          const { done, value } = await reader.read()
          if (done) {
            const trailing = decoder.decode()
            if (trailing) processChunk(trailing)
            finishStream()
            return
          }
          if (value) processChunk(decoder.decode(value, { stream: true }))
        }
      } catch (error) {
        if (!state.stopped) {
          const readError = errorFromException(error, 'Combat stream failed while reading.')
          readError.seq = state.lastEventSequence ?? state.lastSequencedEvent ?? null
          readError.frame_index = state.frameIndex
          stopWithError(state, readError)
        }
      }
    }

    void readStream()
    return state
  }).catch(error => {
    stopWithError(placeholder, errorFromException(error))
    return placeholder
  })

  placeholder.creatingPromise = creatingPromise
  return creatingPromise
}

export function useCombatSSEBuffer(token: string) {
  const [bufferedEvents, setBufferedEvents] = useState<CombatEvent[]>([])
  const [isBufferedComplete, setIsBufferedComplete] = useState(false)
  const [combatError, setCombatError] = useState<CombatTransportError | null>(null)

  useEffect(() => {
    let disposed = false
    let cleanupListener: (() => void) | undefined

    if (!token) {
      setBufferedEvents([])
      setIsBufferedComplete(false)
      setCombatError({
        type: 'error',
        code: 'missing_auth_token',
        message: 'Nie udało się uruchomić walki. Brak tokenu uwierzytelniającego.',
        retriable: false,
      })
      return () => { disposed = true }
    }

    setBufferedEvents([])
    setIsBufferedComplete(false)
    setCombatError(null)

    const setup = async () => {
      try {
        const state = await ensureSharedSSE(token)
        if (disposed) return

        setBufferedEvents([...state.bufferedEvents])
        setIsBufferedComplete(state.isBufferedComplete)
        setCombatError(state.combatError)

        const listener = ({ bufferedEvents: nextEvents, isBufferedComplete: complete, combatError: error }: SharedSSESnapshot) => {
          setBufferedEvents(nextEvents)
          setIsBufferedComplete(complete)
          setCombatError(error)
        }
        state.listeners.add(listener)
        cleanupListener = () => {
          state.listeners.delete(listener)
          if (state.listeners.size === 0 && !state.eventSource && (!state.endTime || Date.now() - state.endTime >= 10000)) {
            sseMap.delete(token)
          }
        }
      } catch (error) {
        if (!disposed) setCombatError(errorFromException(error))
      }
    }

    const setupPromise = setup()
    return () => {
      disposed = true
      void setupPromise.then(() => cleanupListener?.())
    }
  }, [token])

  return { bufferedEvents, isBufferedComplete, combatError }
}
