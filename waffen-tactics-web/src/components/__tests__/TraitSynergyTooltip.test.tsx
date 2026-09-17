// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import TraitSynergyTooltip from '../TraitSynergyTooltip'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const canonicalTraits = JSON.parse(
  readFileSync(resolve(process.cwd(), '..', 'waffen-tactics', 'traits.json'), 'utf-8'),
).traits as any[]

vi.mock('../../data/units', () => ({
  getAllUnits: vi.fn(() => []),
  getCostBorderColor: vi.fn(() => '#6b7280'),
}))

describe('TraitSynergyTooltip canonical description rendering', () => {
  let root: Root | null = null

  afterEach(() => {
    act(() => root?.unmount())
    root = null
    document.body.replaceChildren()
  })

  it('renders the plain-language description for every trait without the technical effect panel', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    for (const traitData of canonicalTraits) {
      act(() => {
        root = createRoot(container)
        root.render(
          <TraitSynergyTooltip
            traitName={traitData.name}
            data={{ count: traitData.thresholds.at(-1), tier: traitData.thresholds.length }}
            traitData={traitData}
          />,
        )
      })

      const trigger = container.querySelector('[role="button"]') as HTMLElement
      act(() => trigger.dispatchEvent(new MouseEvent('click', { bubbles: true })))

      const tooltip = document.body.querySelector('[data-trait-tooltip]') as HTMLElement
      expect(tooltip).not.toBeNull()
      expect(tooltip.querySelectorAll('[data-trait-effect-details]')).toHaveLength(0)
      expect(tooltip.textContent).not.toContain('Do review')
      expect(tooltip.textContent).not.toMatch(/\d[.,]?\d*\/\d/)
      expect(tooltip.textContent).not.toContain('Trigger:')
      expect(tooltip.textContent).not.toContain('Lifecycle:')
      expect(tooltip.textContent).not.toContain('Odświeżanie:')
      expect(tooltip.textContent).toContain(`Tier ${traitData.thresholds.length}`)

      act(() => root?.unmount())
      root = null
      container.replaceChildren()
      document.body.querySelector('[data-trait-tooltip]')?.remove()
    }
  })
})
