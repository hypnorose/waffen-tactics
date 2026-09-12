import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it } from 'vitest'
import GameShell from '../GameShell'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('GameShell', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  it('keeps header and content as separate layout boundaries', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(
        <GameShell contentDisabled header={<header data-testid="game-header">Header</header>}>
          <div data-testid="game-content">Content</div>
        </GameShell>,
      )
    })

    expect(container.querySelector('[data-testid="game-header"]')?.textContent).toBe('Header')
    const content = container.querySelector('main')
    expect(content?.contains(container.querySelector('[data-testid="game-content"]'))).toBe(true)
    expect(content?.className).toContain('pointer-events-none')
    expect(content?.className).toContain('opacity-50')
  })
})

