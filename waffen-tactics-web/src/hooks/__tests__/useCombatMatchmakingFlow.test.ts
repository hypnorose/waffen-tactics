// @vitest-environment jsdom
import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useCombatMatchmakingFlow } from '../useCombatMatchmakingFlow'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

function Probe() {
  const flow = useCombatMatchmakingFlow()
  return createElement('output', {
    'data-phase': flow.matchmakingPhase,
    'data-candidate': flow.rouletteCandidate,
    'data-visible': String(flow.showMatchmakingOverlay),
    'data-replay-gate': String(flow.replayGateOpen),
  })
}

describe('useCombatMatchmakingFlow', () => {
  let root: Root | null = null

  beforeEach(() => vi.useFakeTimers())

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
    vi.useRealTimers()
  })

  it('opens the replay gate only after the intro completes', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(Probe))
    })

    const probe = () => container.querySelector('output') as HTMLOutputElement
    expect(probe().getAttribute('data-phase')).toBe('searching')
    expect(probe().getAttribute('data-visible')).toBe('true')
    expect(probe().getAttribute('data-replay-gate')).toBe('false')

    act(() => vi.advanceTimersByTime(2000))
    expect(probe().getAttribute('data-phase')).toBe('final')
    expect(probe().getAttribute('data-replay-gate')).toBe('false')

    act(() => vi.advanceTimersByTime(1000))
    expect(probe().getAttribute('data-phase')).toBe('done')
    expect(probe().getAttribute('data-visible')).toBe('false')
    expect(probe().getAttribute('data-replay-gate')).toBe('true')
  })

  it('cleans up the intro timers when the owner unmounts', () => {
    const clearTimeoutSpy = vi.spyOn(globalThis, 'clearTimeout')
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(Probe))
    })
    act(() => root?.unmount())
    root = null

    expect(clearTimeoutSpy).toHaveBeenCalledTimes(2)
    clearTimeoutSpy.mockRestore()
  })
})
