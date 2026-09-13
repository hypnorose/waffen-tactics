// @vitest-environment jsdom
import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'
import DesyncInspector from '../DesyncInspector'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('DesyncInspector', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  it('renders the diagnostic log with canonical event identity', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(createElement(DesyncInspector, {
        desyncLogs: [{
          unit_id: 'opp_7',
          unit_name: 'EmptyMelancholy',
          seq: 239,
          event_id: 'combat:239',
          timestamp: 0,
          diff: { defense: { ui: 2047, server: 2055 } },
          pending_events: [],
          note: 'event effect_expired diff (opponent)',
        }],
        onClear: vi.fn(),
        onExport: () => '[]',
      }))
    })

    expect(container.querySelector('#desync-inspector')).not.toBeNull()
    expect(container.textContent).toContain('Desync log (1)')
    expect(container.textContent).toContain('seq:239')
    expect(container.textContent).toContain('event:combat:239')
  })
})
