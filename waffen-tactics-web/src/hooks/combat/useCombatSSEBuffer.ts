import { useState, useEffect } from 'react'
import { CombatEvent } from './types'

// Shared SSE state per token so hot-reload / remounts reuse the same EventSource
type SharedSSEState = {
  eventSource: any // Not actually EventSource anymore, but keeping for compatibility
  ingest: CombatEvent[]
  bufferedEvents: CombatEvent[]
  isBufferedComplete: boolean
  listeners: Set<(state: { bufferedEvents: CombatEvent[]; isBufferedComplete: boolean }) => void>
  creatingPromise?: Promise<SharedSSEState>
  endTime?: number // timestamp when 'end' received, for TTL
}

// Persist map across HMR in dev
if (!(window as any).__combatSSEMap) {
  (window as any).__combatSSEMap = new Map()
}
const sseMap: Map<string, SharedSSEState> = (window as any).__combatSSEMap
let connectionCounter = 0

function ensureSharedSSE(token: string) {
  if (!token) throw new Error('No token')
  const existing = sseMap.get(token)
  if (existing) {
    if (existing.creatingPromise) {
      console.log(`[SSE DEBUG] Token ${token}: Waiting for ongoing creation`)
      return existing.creatingPromise
    }
    // If there's an active connection (indicator in eventSource), reuse it.
    if (existing.eventSource) {
      console.log(`[SSE DEBUG] Token ${token}: Reusing active connection`)
      return Promise.resolve(existing)
    }
    // If the existing entry represents an ended/inactive stream, do not reuse it
    // for new combat starts — delete it so we create a fresh POST + stream.
    console.log(`[SSE DEBUG] Token ${token}: Existing connection inactive/ended — creating new one`)
    sseMap.delete(token)
  }

  console.log(`[SSE DEBUG] Token ${token}: Starting creation, stack:`, new Error().stack)
  const connectionId = ++connectionCounter
  console.log(`[SSE DEBUG] Token ${token}: New connectionId ${connectionId}`)

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  const url = `${API_URL}/game/combat`
  
  // Placeholder in map to prevent races
  const placeholder: SharedSSEState = {
    eventSource: null,
    ingest: [],
    bufferedEvents: [],
    isBufferedComplete: false,
    listeners: new Set(),
    creatingPromise: undefined
  }
  sseMap.set(token, placeholder)

  const creatingPromise = new Promise<SharedSSEState>((resolve) => {
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token }),
    }).then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      if (!response.body) {
        throw new Error('No response body')
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      const state: SharedSSEState = {
        eventSource: {}, // Dummy to indicate active
        ingest: [],
        bufferedEvents: [],
        isBufferedComplete: false,
        listeners: new Set()
      }

      const processChunk = (chunk: string) => {
        buffer += chunk
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6)
            try {
              const data: CombatEvent = JSON.parse(dataStr)
              console.log(`[SSE DEBUG] Token ${token} ConnId ${connectionId}: Received ${data.type} seq:${data.seq}`)
              if (!state.isBufferedComplete) {
                state.ingest.push(data)
                if (data.type === 'end') {
                  state.endTime = Date.now()
                  state.eventSource = null // Mark as ended
                  console.log(`[SSE DEBUG] Token ${token} ConnId ${connectionId}: End received, setting TTL`)
                  const sorted = [...state.ingest].sort((a, b) => {
                    const seqA = a.seq ?? Number.MAX_SAFE_INTEGER
                    const seqB = b.seq ?? Number.MAX_SAFE_INTEGER
                    if (seqA !== seqB) return seqA - seqB
                    const tsA = a.timestamp ?? 0 
                    const tsB = b.timestamp ?? 0
                    return tsA - tsB
                  })
                  state.bufferedEvents = sorted
                  state.isBufferedComplete = true
                  // notify listeners
                  console.log(`[SSE DEBUG] Token ${token} ConnId ${connectionId}: Notifying ${state.listeners.size} listeners`)
                  state.listeners.forEach(l => l({ bufferedEvents: state.bufferedEvents, isBufferedComplete: true }))
                  // Allow live updates for a short time, then close
                  setTimeout(() => {
                    console.log(`[SSE DEBUG] Token ${token} ConnId ${connectionId}: Closing after timeout`)
                    // No close method, just stop reading
                  }, 5000)
                }
              } else {
                // live update
                state.bufferedEvents = [...state.bufferedEvents, data]
                state.listeners.forEach(l => l({ bufferedEvents: state.bufferedEvents, isBufferedComplete: true }))
              }
            } catch (err) {
              console.error('Error parsing combat event', err)
            }
          }
        }
      }

      const readStream = () => {
        reader.read().then(({ done, value }) => {
          if (done) {
            console.log(`[SSE DEBUG] Token ${token} ConnId ${connectionId}: Stream ended`)
            return
          }
          const chunk = decoder.decode(value, { stream: true })
          processChunk(chunk)
          readStream()
        }).catch(err => {
          console.error(`[SSE DEBUG] Token ${token} ConnId ${connectionId}: Stream error`, err)
        })
      }

      readStream()

      // Update map with real state
      sseMap.set(token, state)
      resolve(state)
    }).catch(err => {
      console.error(`[SSE DEBUG] Token ${token} ConnId ${connectionId}: Fetch error`, err)
      // Remove placeholder on error
      sseMap.delete(token)
    })
  })

  placeholder.creatingPromise = creatingPromise
  return creatingPromise
}

export function useCombatSSEBuffer(token: string) {
  const [bufferedEvents, setBufferedEvents] = useState<CombatEvent[]>([])
  const [isBufferedComplete, setIsBufferedComplete] = useState(false)

  useEffect(() => { 
    if (!token) {
      console.error('No token found!')
      return
    }

    let state: SharedSSEState
    const setup = async () => {
      try {
        state = await ensureSharedSSE(token)
        console.log(`[SSE DEBUG] Token ${token}: Setup complete, listeners.size: ${state.listeners.size}`)
      } catch (err) {
        console.error('Failed to ensure shared SSE', err)
        return
      }

      // Initialize local state from shared
      setBufferedEvents(state.bufferedEvents)
      setIsBufferedComplete(state.isBufferedComplete)

      const listener = ({ bufferedEvents: be, isBufferedComplete: ic }: { bufferedEvents: CombatEvent[]; isBufferedComplete: boolean }) => {
        setBufferedEvents(be)
        setIsBufferedComplete(ic)
      }
      state.listeners.add(listener)
      console.log(`[SSE DEBUG] Token ${token}: Added listener, now listeners.size: ${state.listeners.size}`)

      // Cleanup subscription on unmount
      return () => {
        state.listeners.delete(listener)
        console.log(`[SSE DEBUG] Token ${token}: Removed listener, now listeners.size: ${state.listeners.size}`)
        // If no listeners remain and the stream is closed and TTL passed, remove from map
        if (state.listeners.size === 0 && !state.eventSource && (!state.endTime || Date.now() - state.endTime >= 10000)) {
          console.log(`[SSE DEBUG] Token ${token}: Deleting from map`)
          sseMap.delete(token)
        }
      }
    }

    const cleanup = setup() 
    return () => {
      cleanup.then(clean => clean?.())
    }
  }, [token])

  return { bufferedEvents, isBufferedComplete }
}