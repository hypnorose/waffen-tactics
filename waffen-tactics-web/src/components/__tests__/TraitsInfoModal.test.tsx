// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import TraitsInfoModal from '../TraitsInfoModal'
import { gameAPI } from '../../services/api'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

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
})
