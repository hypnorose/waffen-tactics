// @vitest-environment jsdom
import { act, createElement, type RefObject } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createRoot, type Root } from 'react-dom/client'
import CombatLogModal from '../CombatLogModal'

vi.mock('../CombatLog', () => ({
  default: ({ combatLog }: { combatLog: string[] }) => <div data-testid="combat-log">{combatLog.join('|')}</div>,
}))

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('CombatLogModal responsive shell', () => {
  let root: Root | null = null
  let container: HTMLDivElement | null = null

  afterEach(() => {
    if (root && container) {
      act(() => root?.unmount())
      container.remove()
    }
    root = null
    container = null
  })

  const renderModal = (visible = true) => {
    container = document.createElement('div')
    document.body.appendChild(container)
    const logEndRef = { current: null } as RefObject<HTMLDivElement>
    const setShowLog = vi.fn()
    act(() => {
      root = createRoot(container as HTMLDivElement)
      root.render(createElement(CombatLogModal, {
        showLog: true,
        visible,
        setShowLog,
        combatLog: ['[ATK] Replay event'],
        logEndRef,
      }))
    })
    return { setShowLog }
  }

  it('uses responsive CSS classes and dialog semantics instead of fixed inline geometry', () => {
    renderModal()
    const modal = container?.querySelector('#combat-log-modal') as HTMLElement

    expect(modal.getAttribute('role')).toBe('dialog')
    expect(modal.getAttribute('aria-labelledby')).toBe('combat-log-modal-title')
    expect(modal.getAttribute('aria-hidden')).toBe('false')
    expect(modal.dataset.visible).toBe('true')
    expect(modal.getAttribute('style')).toBeNull()
    expect(modal.querySelector('.combat-log-modal-header')).not.toBeNull()
    expect(modal.querySelector('.combat-log-modal-content')).not.toBeNull()
    expect(modal.querySelector('[aria-label="Close combat log"]')).not.toBeNull()
  })

  it('keeps the mounted log hidden when the combat sidebar collapses', () => {
    renderModal(false)
    const modal = container?.querySelector('#combat-log-modal') as HTMLElement

    expect(modal.dataset.visible).toBe('false')
    expect(modal.getAttribute('aria-hidden')).toBe('true')
    expect(modal.textContent).toContain('Replay event')
  })

  it('delegates close action to the overlay state owner', () => {
    const { setShowLog } = renderModal()
    act(() => (container?.querySelector('.combat-log-close') as HTMLButtonElement).click())

    expect(setShowLog).toHaveBeenCalledWith(false)
  })
})
