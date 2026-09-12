import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it } from 'vitest'
import { Badge, Button, Panel, ProgressBar } from '../primitives'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('UI primitives', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  it('exposes semantic button and panel variants without hiding native behavior', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(
        <Panel variant="raised" aria-label="Login panel">
          <Button variant="primary" disabled>Continue</Button>
          <Badge tone="accent">Set 2</Badge>
        </Panel>,
      )
    })

    expect(container.querySelector('.ui-panel--raised')).not.toBeNull()
    expect(container.querySelector('.ui-button--primary')).toHaveProperty('disabled', true)
    expect(container.querySelector('.ui-badge--accent')?.textContent).toBe('Set 2')
  })

  it('clamps progress values and exposes an accessible numeric contract', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(<ProgressBar value={140} max={100} label="Health" />)
    })

    const progress = container.querySelector('[role="progressbar"]')
    expect(progress?.getAttribute('aria-label')).toBe('Health')
    expect(progress?.getAttribute('aria-valuenow')).toBe('100')
    expect((container.querySelector('.ui-progress__fill') as HTMLElement | null)?.style.width).toBe('100%')
  })
})
