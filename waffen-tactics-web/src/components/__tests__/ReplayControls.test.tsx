// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import ReplayControls from '../ReplayControls'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('ReplayControls', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  const renderControls = (overrides: Partial<React.ComponentProps<typeof ReplayControls>> = {}) => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    act(() => {
      root = createRoot(container)
      root.render(createElement(ReplayControls, {
        eventCount: 3,
        currentIndex: 1,
        currentEvent: { type: 'mana_update', seq: 12, timestamp: 1.5 },
        isPlaying: true,
        onRestart: vi.fn(),
        onTogglePlay: vi.fn(),
        onSeek: vi.fn(),
        ...overrides,
      }))
    })
    return container
  }

  it('exposes restart, pause and an accessible timeline status', () => {
    const onRestart = vi.fn()
    const onTogglePlay = vi.fn()
    const container = renderControls({ onRestart, onTogglePlay })

    expect(container.textContent).toContain('Zdarzenie 2 z 3')
    expect(container.textContent).toContain('t=1.50 s')
    expect(container.querySelector('[aria-label="Uruchom replay od początku"]')).not.toBeNull()
    expect(container.querySelector('[aria-label="Wstrzymaj replay"]')).not.toBeNull()

    act(() => (container.querySelector('[aria-label="Uruchom replay od początku"]') as HTMLButtonElement).click())
    act(() => (container.querySelector('[aria-label="Wstrzymaj replay"]') as HTMLButtonElement).click())

    expect(onRestart).toHaveBeenCalledOnce()
    expect(onTogglePlay).toHaveBeenCalledOnce()
  })

  it('reports an invalid seek error without hiding the controls', () => {
    const container = renderControls({ error: 'Pozycja replayu jest niedostępna.' })

    expect(container.querySelector('[role="alert"]')?.textContent).toContain('niedostępna')
    expect(container.querySelector('[aria-label="Pozycja replayu"]')).not.toBeNull()
  })
})
