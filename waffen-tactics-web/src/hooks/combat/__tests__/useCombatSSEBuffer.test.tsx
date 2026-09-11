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
    ].join('\n')
    const reader = {
      read: vi.fn(async () => {
        if (readCount++ > 0) return { done: true, value: undefined }
        return { done: false, value: new TextEncoder().encode(frame) }
      }),
      cancel,
    }

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      body: { getReader: () => reader },
    }))

    let latest: BufferState | null = null
    const container = document.createElement('div')
    document.body.appendChild(container)
    await act(async () => {
      root = createRoot(container)
      root.render(createElement(BufferProbe, {
        token: 'test-token-invalid-input',
        onState: state => { latest = state },
      }))
      await new Promise(resolve => setTimeout(resolve, 0))
      await new Promise(resolve => setTimeout(resolve, 0))
    })

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
