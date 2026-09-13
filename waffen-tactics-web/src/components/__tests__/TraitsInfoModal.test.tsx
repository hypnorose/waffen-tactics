// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import TraitsInfoModal from '../TraitsInfoModal'
import { gameAPI } from '../../services/api'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const canonicalTraits = JSON.parse(
  readFileSync(resolve(process.cwd(), '..', 'waffen-tactics', 'traits.json'), 'utf-8'),
).traits as any[]

vi.mock('../../services/api', () => ({
  gameAPI: {
    getTraits: vi.fn(),
    getUnits: vi.fn(),
  },
}))

vi.mock('../../data/units', () => ({
  getCostColor: vi.fn(() => 'text-gray-400'),
}))

describe('TraitsInfoModal canonical descriptions', () => {
  let root: Root | null = null

  beforeEach(() => {
    vi.mocked(gameAPI.getTraits).mockResolvedValue({
      data: [{
        name: 'Konfident',
        description: 'Base description',
        type: 'class',
        thresholds: [1],
        threshold_descriptions: ['Canonical resolved description'],
        modular_effects: [[{
          rewards: [{ type: 'stat_buff', stat: 'attack', value: 999 }],
        }]],
      }],
    } as any)
    vi.mocked(gameAPI.getUnits).mockResolvedValue({
      data: [{ id: 'unit-1', name: 'Unit One', cost: 1, traits: ['Konfident'] }],
    } as any)
  })

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
    vi.clearAllMocks()
  })

  it('renders the backend-resolved threshold description without client-side reward inference', async () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    await act(async () => {
      root = createRoot(container)
      root.render(<TraitsInfoModal isOpen onClose={vi.fn()} />)
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    expect(container.textContent).toContain('Canonical resolved description')
    expect(container.textContent).not.toContain('999')
  })

  it('renders every canonical tier and effect from the full API matrix', async () => {
    vi.mocked(gameAPI.getTraits).mockResolvedValue({ data: canonicalTraits } as any)
    vi.mocked(gameAPI.getUnits).mockResolvedValue({ data: [] } as any)
    const container = document.createElement('div')
    document.body.appendChild(container)

    await act(async () => {
      root = createRoot(container)
      root.render(<TraitsInfoModal isOpen onClose={vi.fn()} />)
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    const expectedEffectCount = canonicalTraits.reduce(
      (count, trait) => count + trait.modular_effects.flat().length,
      0,
    )
    expect(container.querySelectorAll('[data-trait-effect-details]')).toHaveLength(expectedEffectCount)
    expect(container.textContent).not.toContain('Do review')
    expect(container.textContent).not.toMatch(/\d[.,]?\d*\/\d/)
    expect(container.querySelectorAll('.traits-modal-content > div > div')).toHaveLength(canonicalTraits.length)
  })
})
