// @vitest-environment jsdom
import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it } from 'vitest'
import CombatWindowStatusOverlays from '../CombatWindowStatusOverlays'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('CombatWindowStatusOverlays', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  it('renders the supplied matchmaking state without owning its timer', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatWindowStatusOverlays, {
        combatError: null,
        showMatchmakingOverlay: true,
        matchmakingPhase: 'searching',
        rouletteCandidate: 'Candidate A',
        showVictoryOverlay: false,
        victory: null,
      }))
    })

    expect(container.textContent).toContain('Szukanie przeciwnika')
    expect(container.textContent).toContain('Candidate A')
    expect(container.querySelector('[role="alert"]')).toBeNull()
  })

  it('keeps error and result semantics in the presentation layer', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatWindowStatusOverlays, {
        combatError: { code: 'replay_invalid', message: 'Replay rejected', retriable: false },
        showMatchmakingOverlay: false,
        matchmakingPhase: 'done',
        rouletteCandidate: 'Candidate A',
        showVictoryOverlay: true,
        victory: false,
        defeatMessage: 'Defeat',
      }))
    })

    expect(container.querySelector('[role="alert"]')?.textContent).toContain('Replay rejected')
    expect(container.textContent).toContain('Defeat')
  })
})
