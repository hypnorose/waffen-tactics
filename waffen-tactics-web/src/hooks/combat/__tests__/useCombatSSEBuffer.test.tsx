// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, createElement, useEffect, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { classifyCombatSSEFrame, useCombatSSEBuffer } from '../useCombatSSEBuffer'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

type BufferState = ReturnType<typeof useCombatSSEBuffer>

function BufferProbe({ token, onState }: { token: string, onState: (state: BufferState) => void }): ReactNode {
  const state = useCombatSSEBuffer(token)
  useEffect(() => onState(state), [onState, state])
  return null
}

describe('useCombatSSEBuffer', () => {
  let root: Root | null = null

  async function renderBuffer(response: unknown, token = 'test-token') {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))
    let latest: BufferState | null = null
    const container = document.createElement('div')
    document.body.appendChild(container)

    await act(async () => {
      root = createRoot(container)
      root.render(createElement(BufferProbe, {
        token,
        onState: state => { latest = state },
      }))
      await new Promise(resolve => setTimeout(resolve, 0))
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    return latest
  }

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
    ;(window as any).__combatSSEMap?.clear()
    vi.unstubAllGlobals()
  })

  it('keeps invalid_combat_input outside replay and stops the stream', async () => {
    const cancel = vi.fn().mockResolvedValue(undefined)
    let readCount = 0
    const frame = [
      `data: ${JSON.stringify({ type: 'units_init', player_units: [], opponent_units: [], seq: 1 })}`,
      `data: ${JSON.stringify({
        type: 'error',
        code: 'invalid_combat_input',
        retriable: false,
        message: 'Combat data is invalid. Please refresh and try again.',
      })}`,
      `data: ${JSON.stringify({ type: 'end', seq: 1000000 })}`,
      '',
    ].join('\n\n')
    const reader = {
      read: vi.fn(async () => {
        if (readCount++ > 0) return { done: true, value: undefined }
        return { done: false, value: new TextEncoder().encode(frame) }
      }),
      cancel,
    }

    const latest = await renderBuffer({
      ok: true,
      body: { getReader: () => reader },
    }, 'test-token-invalid-input')

    expect(latest).not.toBeNull()
    expect(latest?.bufferedEvents.map(event => event.type)).toEqual(['units_init'])
    expect(latest?.bufferedEvents.some(event => event.type === 'error')).toBe(false)
    expect(latest?.isBufferedComplete).toBe(false)
    expect(latest?.combatError).toEqual({
      type: 'error',
      code: 'invalid_combat_input',
      retriable: false,
      message: 'Combat data is invalid. Please refresh and try again.',
    })
    expect(cancel).toHaveBeenCalledOnce()
    expect(reader.read).toHaveBeenCalledOnce()
  })

  it('surfaces a fetch rejection instead of leaving the combat request pending', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network offline')))

    let latest: BufferState | null = null
    const container = document.createElement('div')
    document.body.appendChild(container)
    await act(async () => {
      root = createRoot(container)
      root.render(createElement(BufferProbe, {
        token: 'test-token-fetch-error',
        onState: state => { latest = state },
      }))
      await new Promise(resolve => setTimeout(resolve, 0))
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    expect(latest?.bufferedEvents).toEqual([])
    expect(latest?.isBufferedComplete).toBe(false)
    expect(latest?.combatError).toMatchObject({
      type: 'error',
      code: 'combat_stream_failed',
      retriable: true,
    })
    expect(latest?.combatError?.message).toContain('network offline')
  })

  it('maps a non-2xx response to a visible server error', async () => {
    const latest = await renderBuffer({
      ok: false,
      status: 409,
      json: vi.fn().mockResolvedValue({ code: 'player_action_conflict', error: 'Retry the combat action.' }),
    }, 'test-token-http-error')

    expect(latest?.combatError).toEqual({
      type: 'error',
      code: 'player_action_conflict',
      message: 'Retry the combat action.',
      retriable: false,
    })
    expect(latest?.bufferedEvents).toEqual([])
  })

  it('surfaces reader errors while preserving already received frames and never marks the stream complete', async () => {
    const reader = {
      read: vi.fn()
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode(`data: ${JSON.stringify({ type: 'units_init', seq: 0 })}\n\n`),
        })
        .mockRejectedValueOnce(new Error('connection reset')),
      cancel: vi.fn().mockResolvedValue(undefined),
    }
    const latest = await renderBuffer({ ok: true, body: { getReader: () => reader } }, 'test-token-read-error')

    expect(latest?.bufferedEvents.map(event => event.type)).toEqual(['units_init'])
    expect(latest?.isBufferedComplete).toBe(false)
    expect(latest?.combatError).toMatchObject({
      code: 'combat_stream_failed',
      retriable: true,
      seq: 0,
      frame_index: 1,
    })
    expect(latest?.combatError?.message).toContain('connection reset')
    expect(reader.cancel).toHaveBeenCalledOnce()
  })

  it('fails closed on malformed JSON and invalid frame objects', async () => {
    const malformed = await renderBuffer({
      ok: true,
      body: {
        getReader: () => ({
          read: vi.fn().mockResolvedValueOnce({ done: false, value: new TextEncoder().encode('data: {broken-json}\n\n') }),
          cancel: vi.fn().mockResolvedValue(undefined),
        }),
      },
    }, 'test-token-malformed-json')
    expect(malformed?.combatError).toMatchObject({ code: 'combat_malformed_frame', frame_index: 1 })

    act(() => root?.unmount())
    root = null
    document.body.replaceChildren()
    ;(window as any).__combatSSEMap?.clear()

    const invalidObject = await renderBuffer({
      ok: true,
      body: {
        getReader: () => ({
          read: vi.fn().mockResolvedValueOnce({ done: false, value: new TextEncoder().encode('data: {"payload":true}\n\n') }),
          cancel: vi.fn().mockResolvedValue(undefined),
        }),
      },
    }, 'test-token-invalid-frame')
    expect(invalidObject?.combatError).toMatchObject({ code: 'combat_malformed_frame', frame_index: 1 })
  })

  it('fails on premature EOF without a terminal end frame', async () => {
    const reader = {
      read: vi.fn()
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode(`data: ${JSON.stringify({ type: 'units_init', seq: 0 })}\n\n`),
        })
        .mockResolvedValueOnce({ done: true, value: undefined }),
      cancel: vi.fn().mockResolvedValue(undefined),
    }
    const latest = await renderBuffer({ ok: true, body: { getReader: () => reader } }, 'test-token-eof')

    expect(latest?.bufferedEvents.map(event => event.type)).toEqual(['units_init'])
    expect(latest?.isBufferedComplete).toBe(false)
    expect(latest?.combatError).toMatchObject({ code: 'combat_stream_eof', seq: 0, frame_index: 1 })
  })

  it('rejects sequence gaps and conflicting duplicate event identities', async () => {
    const gap = await renderBuffer({
      ok: true,
      body: {
        getReader: () => ({
          read: vi.fn().mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode([
              `data: ${JSON.stringify({ type: 'units_init', seq: 0 })}`,
              `data: ${JSON.stringify({ type: 'start', seq: 0 })}`,
              `data: ${JSON.stringify({ type: 'unit_attack', seq: 2, event_id: 'combat:2' })}`,
              '',
            ].join('\n\n')),
          }),
          cancel: vi.fn().mockResolvedValue(undefined),
        }),
      },
    }, 'test-token-sequence-gap')
    expect(gap?.combatError).toMatchObject({ code: 'combat_sequence_gap', seq: 2, event_id: 'combat:2' })
    expect(gap?.bufferedEvents.map(event => event.type)).toEqual(['units_init', 'start'])

    act(() => root?.unmount())
    root = null
    document.body.replaceChildren()
    ;(window as any).__combatSSEMap?.clear()

    const conflict = await renderBuffer({
      ok: true,
      body: {
        getReader: () => ({
          read: vi.fn().mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode([
              `data: ${JSON.stringify({ type: 'units_init', seq: 0 })}`,
              `data: ${JSON.stringify({ type: 'unit_attack', seq: 1, event_id: 'combat:1', amount: 1 })}`,
              `data: ${JSON.stringify({ type: 'unit_attack', seq: 1, event_id: 'combat:1', amount: 2 })}`,
              '',
            ].join('\n\n')),
          }),
          cancel: vi.fn().mockResolvedValue(undefined),
        }),
      },
    }, 'test-token-conflicting-duplicate')
    expect(conflict?.combatError).toMatchObject({ code: 'combat_conflicting_duplicate', seq: 1, event_id: 'combat:1' })
    expect(conflict?.bufferedEvents.map(event => event.type)).toEqual(['units_init', 'unit_attack'])
  })

  it('deduplicates identical frames and completes only after the terminal end event', async () => {
    const combatEvent = { type: 'damage', seq: 1, event_id: 'combat:1' }
    const frame = [
      { type: 'units_init', seq: 0 },
      { type: 'start', seq: 0 },
      combatEvent,
      combatEvent,
      { type: 'victory', seq: 999998 },
      { type: 'gold_income', seq: 999997 },
      { type: 'end', seq: 1000000 },
    ].map(event => `data: ${JSON.stringify(event)}`).concat('').join('\n\n')
    const reader = {
      read: vi.fn()
        .mockResolvedValueOnce({ done: false, value: new TextEncoder().encode(frame) })
        .mockResolvedValueOnce({ done: true, value: undefined }),
      cancel: vi.fn().mockResolvedValue(undefined),
    }
    const latest = await renderBuffer({ ok: true, body: { getReader: () => reader } }, 'test-token-complete')

    expect(latest?.bufferedEvents.map(event => event.type)).toEqual(['units_init', 'start', 'damage', 'victory', 'gold_income', 'end'])
    expect(latest?.isBufferedComplete).toBe(true)
    expect(latest?.combatError).toBeNull()
  })

  it('classifies valid canonical frames as replay events and transport errors separately', () => {
    expect(classifyCombatSSEFrame({ type: 'units_init', seq: 1 })).toEqual({
      kind: 'event',
      event: { type: 'units_init', seq: 1 },
    })
    expect(classifyCombatSSEFrame({ type: 'error', message: 'safe', retriable: true })).toEqual({
      kind: 'error',
      error: {
        type: 'error',
        code: 'combat_request_failed',
        message: 'safe',
        retriable: true,
      },
    })
    expect(classifyCombatSSEFrame({ malformed: true })).toBeNull()
  })
})
