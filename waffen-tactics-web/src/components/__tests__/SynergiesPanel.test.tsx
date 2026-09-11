// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import SynergiesPanel from '../SynergiesPanel'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('SynergiesPanel trait tooltip ownership', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  it('uses the viewport-safe portal and renders every canonical threshold', () => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1280 })
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 720 })
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(
        <SynergiesPanel
          synergies={{ Starociota: { count: 3, tier: 1 } }}
          traits={[{
            name: 'Starociota',
            type: 'faction',
            thresholds: [2, 3, 5],
            threshold_descriptions: ['+10/20/30 obrony i +2/4/6 HP/s; bez kumulacji.'],
            modular_effects: [[], [], []],
          } as any]}
        />,
      )
    })

    const trigger = container.querySelector('[aria-label="Starociota, 3 jednostek, Tier 1"]') as HTMLElement
    expect(trigger).not.toBeNull()
    trigger.getBoundingClientRect = () => ({
      top: 8,
      bottom: 32,
      left: 300,
      right: 420,
      width: 120,
      height: 24,
      x: 300,
      y: 8,
      toJSON: () => ({}),
    })

    act(() => {
      trigger.click()
    })

    const tooltip = document.body.querySelector('[data-trait-tooltip]') as HTMLElement
    expect(tooltip).not.toBeNull()
    expect(tooltip.parentElement).toBe(document.body)
    expect(tooltip.style.position).toBe('fixed')
    expect(tooltip.dataset.tooltipPlacement).toBe('below')
    expect(tooltip.textContent).toContain('[2] Tier 1')
    expect(tooltip.textContent).toContain('[3] Tier 2')
    expect(tooltip.textContent).toContain('[5] Tier 3')
    expect(tooltip.textContent).toContain('+10 obrony i +2 HP/s')
    expect(tooltip.textContent).toContain('+20 obrony i +4 HP/s')
    expect(tooltip.textContent).toContain('+30 obrony i +6 HP/s')
    expect(tooltip.textContent).not.toContain('+10/20/30')
  })

  it('does not render zero-count entries as active synergy controls', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    act(() => {
      root = createRoot(container)
      root.render(
        <SynergiesPanel
          synergies={{ Starociota: { count: 0, tier: 0 } }}
          traits={[]}
        />,
      )
    })

    expect(container.querySelector('[role="button"]')).toBeNull()
  })
})
