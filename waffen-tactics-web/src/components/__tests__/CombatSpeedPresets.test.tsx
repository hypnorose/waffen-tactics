// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import CombatSpeedPresets from '../CombatSpeedPresets'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('CombatSpeedPresets', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  it('exposes exactly the approved 1x, 2x and 5x replay presets', () => {
    const setCombatSpeed = vi.fn()
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(CombatSpeedPresets, { combatSpeed: 2, setCombatSpeed }))
    })

    const buttons = [...container.querySelectorAll('button')]
    expect(buttons.map(button => button.textContent)).toEqual(['1×', '2×', '5×'])
    expect(container.querySelector('input[type="range"]')).toBeNull()
    expect(buttons.map(button => button.getAttribute('aria-pressed'))).toEqual(['false', 'true', 'false'])

    act(() => buttons[2].click())
    expect(setCombatSpeed).toHaveBeenCalledWith(5)
  })
})
