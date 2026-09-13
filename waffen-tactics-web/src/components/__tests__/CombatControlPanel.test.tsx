// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import CombatControlPanel from '../CombatControlPanel'

vi.mock('../CombatHeader', () => ({ default: () => null }))
vi.mock('../CombatSummaryPanel', () => ({ default: () => null }))
vi.mock('../CombatActionQueue', () => ({ default: () => null }))
vi.mock('../SynergiesPanel', () => ({ default: () => null }))
vi.mock('../CombatSpeedPresets', () => ({ default: () => null }))

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const baseProps = {
  expanded: true,
  opponentInfo: null,
  combatSummary: null,
  synergies: {},
  traits: [],
  replayEvents: [],
  replayEventIndex: 0,
  combatSpeed: 1,
  setCombatSpeed: vi.fn(),
  isFinished: false,
  storedGoldBreakdown: null,
  displayedGoldBreakdown: null,
  setDisplayedGoldBreakdown: vi.fn(),
  onContinue: vi.fn(),
}

describe('CombatControlPanel', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  it('keeps the sidebar mounted in the shell contract while collapsed', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatControlPanel, { ...baseProps, expanded: false }))
    })

    const panel = container.querySelector('#combat-control-panel') as HTMLElement
    expect(panel.getAttribute('aria-hidden')).toBe('true')
    expect(panel.style.display).toBe('none')
  })

  it('reveals the continue action only after combat completion', () => {
    const onContinue = vi.fn()
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatControlPanel, { ...baseProps, onContinue, isFinished: true }))
    })

    const button = Array.from(container.querySelectorAll('button')).find((candidate) => candidate.textContent?.includes('Kontynuuj')) as HTMLButtonElement
    expect(button).not.toBeUndefined()
    act(() => button.click())
    expect(onContinue).toHaveBeenCalledTimes(1)
  })
})
