// @vitest-environment jsdom
import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'
import CombatWindowShell from '../CombatWindowShell'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('CombatWindowShell', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  it('keeps stable arena slots and delegates panel controls', () => {
    const onTogglePanel = vi.fn()
    const onToggleLog = vi.fn()
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatWindowShell, {
        expanded: true,
        showLog: false,
        combatPanel: createElement('aside', { id: 'panel-child' }, 'panel'),
        opponentSlot: createElement('div', { id: 'opponent-child' }, 'opponent'),
        playerSlot: createElement('div', { id: 'player-child' }, 'player'),
        log: createElement('div', { id: 'log-child' }, 'log'),
        replayControls: createElement('div', { id: 'replay-child' }, 'replay'),
        onTogglePanel,
        onToggleLog,
      }))
    })

    expect(container.querySelector('.combat-overlay-panel')).not.toBeNull()
    expect(container.querySelector('.combat-opponent-slot #opponent-child')).not.toBeNull()
    expect(container.querySelector('.combat-player-slot #player-child')).not.toBeNull()
    expect(container.querySelector('#panel-child')).not.toBeNull()
    expect(container.querySelector('#log-child')).not.toBeNull()
    expect(container.querySelector('#replay-child')).not.toBeNull()

    act(() => {
      ;(container.querySelector('.combat-panel-toggle') as HTMLButtonElement).click()
      ;(container.querySelector('.combat-log-toggle') as HTMLButtonElement).click()
    })

    expect(onTogglePanel).toHaveBeenCalledTimes(1)
    expect(onToggleLog).toHaveBeenCalledTimes(1)
  })

  it('exposes collapsed state without removing the board controls', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatWindowShell, {
        expanded: false,
        showLog: true,
        combatPanel: createElement('aside'),
        opponentSlot: createElement('div'),
        playerSlot: createElement('div'),
        log: createElement('div'),
        replayControls: createElement('div'),
        onTogglePanel: vi.fn(),
        onToggleLog: vi.fn(),
      }))
    })

    const panelToggle = container.querySelector('.combat-panel-toggle') as HTMLButtonElement
    const logToggle = container.querySelector('.combat-log-toggle') as HTMLButtonElement
    expect(panelToggle.getAttribute('aria-expanded')).toBe('false')
    expect(panelToggle.getAttribute('aria-label')).toBe('Rozwiń panel walki')
    expect(logToggle.getAttribute('aria-expanded')).toBe('true')
  })
})
