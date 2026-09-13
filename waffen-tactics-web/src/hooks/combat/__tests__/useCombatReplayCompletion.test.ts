// @vitest-environment jsdom
import { act, createElement, useRef, useState } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { shouldFinalizeReplay, useCombatReplayCompletion } from '../useCombatReplayCompletion'
import type { CombatState } from '../types'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

function CompletionHarness({ allEventsReplayed, pendingVisuals, onClear }: {
  allEventsReplayed: boolean
  pendingVisuals: number
  onClear: () => void
}) {
  const [combatState, setCombatState] = useState<CombatState>({
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
    activeAnimations: [],
  })
  const combatStateRef = useRef(combatState)

  useCombatReplayCompletion({
    allEventsReplayed,
    pendingVisuals,
    clearPresentationTracks: onClear,
    setCombatState,
    combatStateRef,
  })

  return createElement('output', { 'data-finished': String(combatState.isFinished) })
}

describe('useCombatReplayCompletion', () => {
  let root: Root | null = null
  let container: HTMLDivElement

  beforeEach(() => {
    vi.useFakeTimers()
    container = document.createElement('div')
    document.body.appendChild(container)
  })

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    container.remove()
    vi.useRealTimers()
  })

  it('finalizes only after the canonical stream and visual projection are complete', () => {
    expect(shouldFinalizeReplay(false, 0)).toBe(false)
    expect(shouldFinalizeReplay(true, 1)).toBe(false)
    expect(shouldFinalizeReplay(true, 0)).toBe(true)
  })

  it('marks the combat finished immediately and clears transient tracks after the presentation window', () => {
    const onClear = vi.fn()
    act(() => {
      root = createRoot(container)
      root.render(createElement(CompletionHarness, { allEventsReplayed: true, pendingVisuals: 0, onClear }))
    })

    expect(container.querySelector('output')?.getAttribute('data-finished')).toBe('true')
    expect(onClear).not.toHaveBeenCalled()

    act(() => vi.advanceTimersByTime(499))
    expect(onClear).not.toHaveBeenCalled()

    act(() => vi.advanceTimersByTime(1))
    expect(onClear).toHaveBeenCalledTimes(1)
  })
})
