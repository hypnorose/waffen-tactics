// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import Login from '../Login'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('Login', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  it('does not present stale hardcoded roster counts', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(<Login />)
    })

    expect(container.textContent).toContain('Waffen Tactics')
    expect(container.textContent).toContain('Zaloguj się przez Discord')
    expect(container.textContent).not.toContain('51 jednostek')
    expect(container.textContent).not.toContain('14 traitów')
  })
})
