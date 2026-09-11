// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { CombatOverlayContent } from '../CombatOverlay'
import { useCombatOverlayLogic } from '../../hooks/useCombatOverlayLogic'

vi.mock('../../hooks/useCombatOverlayLogic', () => ({
  useCombatOverlayLogic: vi.fn(),
}))

vi.mock('../../hooks/useUnitAnchors', () => ({
  UnitAnchorsProvider: ({ children }: { children: unknown }) => children,
}))

vi.mock('../../hooks/useProjectileSystem', () => ({
  ProjectileProvider: ({ children }: { children: unknown }) => children,
}))

vi.mock('../GoldNotification', () => ({ default: () => null }))
vi.mock('../CombatHeader', () => ({ default: () => null }))
vi.mock('../PlayerUnits', () => ({ default: () => null }))
vi.mock('../OpponentUnits', () => ({ default: () => null }))
vi.mock('../CombatSummaryPanel', () => ({ default: () => null }))
vi.mock('../SynergiesPanel', () => ({ default: () => null }))
vi.mock('../CombatSpeedSlider', () => ({ default: () => null }))
vi.mock('../ProjectileLayer', () => ({ default: () => null }))
vi.mock('../DesyncInspector', () => ({ default: () => null }))

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const mockLogic = {
  playerUnits: [],
  opponentUnits: [],
  combatLog: ['[ATK] Pierwsze zdarzenie replayu'],
  isFinished: false,
  victory: null,
  finalState: null,
  synergies: {},
  traits: [],
  opponentInfo: null,
  showLog: true,
  setShowLog: vi.fn(),
  combatSpeed: 1,
  setCombatSpeed: vi.fn(),
  regenMap: {},
  storedGoldBreakdown: null,
  displayedGoldBreakdown: null,
  setDisplayedGoldBreakdown: vi.fn(),
  setStoredGoldBreakdown: vi.fn(),
  handleClose: vi.fn(),
  handleGoldDismiss: vi.fn(),
  defeatMessage: '',
  combatSummary: null,
  activeAttackerId: null,
  activeTargetId: null,
  simTime: 0,
  replayEvents: [{ type: 'mana_update', seq: 1, timestamp: 0 }],
  replayEventIndex: 0,
  replayPlaying: true,
  replaySeekError: null,
  combatError: null,
  restartReplay: vi.fn(),
  toggleReplay: vi.fn(),
  seekReplay: vi.fn(),
  desyncLogs: [],
  clearDesyncLogs: vi.fn(),
  exportDesyncJSON: vi.fn(() => '[]'),
  isSearchingOpponent: false,
}

describe('CombatOverlay panel collapse', () => {
  let root: Root | null = null

  beforeEach(() => {
    vi.useFakeTimers()
    vi.mocked(useCombatOverlayLogic).mockReturnValue(mockLogic as ReturnType<typeof useCombatOverlayLogic>)
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1280 })
  })

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
    vi.useRealTimers()
  })

  const renderOverlay = () => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatOverlayContent, { onClose: vi.fn() }))
    })
    act(() => vi.advanceTimersByTime(3000))
    return container
  }

  it('toggles without unmounting the log, preserves focus, and hides replay controls', () => {
    const container = renderOverlay()
    const toggle = container.querySelector('[aria-label="Zwiń panel walki"]') as HTMLButtonElement
    const log = container.textContent || ''

    expect(toggle).not.toBeNull()
    expect(log).toContain('Pierwsze zdarzenie replayu')
    expect(container.querySelector('[aria-label="Sterowanie replayem walki"]')).not.toBeNull()

    act(() => {
      toggle.focus()
      toggle.click()
    })

    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(container.querySelector('#combat-control-panel')?.getAttribute('aria-hidden')).toBe('true')
    expect(container.querySelector('[aria-label="Sterowanie replayem walki"]')?.getAttribute('aria-hidden')).toBe('true')
    expect((container.querySelector('[aria-label="Sterowanie replayem walki"]') as HTMLElement).style.display).toBe('none')
    expect(container.textContent).toContain('Pierwsze zdarzenie replayu')
    expect(document.activeElement).toBe(toggle)
    expect(toggle.className).toContain('combat-panel-toggle')

    act(() => toggle.click())
    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    expect(container.querySelector('#combat-control-panel')?.getAttribute('aria-hidden')).toBe('false')
  })

  it('starts collapsed on a narrow viewport while keeping the board control visible', () => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 800 })
    const container = renderOverlay()

    expect(container.querySelector('[aria-label="Rozwiń panel walki"]')).not.toBeNull()
    expect(container.querySelector('#combat-control-panel')?.getAttribute('aria-hidden')).toBe('true')
  })
})
