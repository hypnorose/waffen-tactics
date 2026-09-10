import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockGet = vi.hoisted(() => vi.fn())

vi.mock('axios', () => ({
  default: {
    get: mockGet,
  },
}))

async function importUnitsModule() {
  vi.resetModules()
  return import('../units')
}

describe('canonical unit data loading', () => {
  beforeEach(() => {
    mockGet.mockReset()
  })

  it('does not expose a hard-coded unit before the canonical API loads', async () => {
    const { getAllUnits, getUnit } = await importUnitsModule()

    expect(getUnit('rafcikd')).toBeUndefined()
    expect(getAllUnits()).toEqual([])
  })

  it('propagates a canonical unit API failure', async () => {
    const failure = new Error('units API offline')
    mockGet.mockRejectedValueOnce(failure)
    const { loadUnits } = await importUnitsModule()

    await expect(loadUnits()).rejects.toThrow('units API offline')
  })

  it('caches successfully loaded canonical units', async () => {
    const unit = {
      id: 'unit_a',
      name: 'Unit A',
      cost: 1,
      factions: [],
      classes: [],
      stats: { hp: 100, attack: 10, defense: 5, attack_speed: 1 },
    }
    mockGet.mockResolvedValueOnce({ data: [unit] })
    const { getAllUnits, getUnit, loadUnits } = await importUnitsModule()

    await loadUnits()
    await loadUnits()

    expect(mockGet).toHaveBeenCalledTimes(1)
    expect(getUnit('unit_a')).toEqual(unit)
    expect(getAllUnits()).toEqual([unit])
  })
})

describe('passive presentation data', () => {
  it('uses the passive name as its display title', async () => {
    const { getPassiveTitle } = await importUnitsModule()

    expect(getPassiveTitle({ name: 'Jajcarz', description: 'Efekt' })).toBe('Jajcarz')
  })

  it('supports title as a compatibility field and has no generic fallback', async () => {
    const { getPassiveTitle } = await importUnitsModule()

    expect(getPassiveTitle({ title: 'Walkover', description: 'Efekt' })).toBe('Walkover')
    expect(getPassiveTitle({ description: 'Efekt' })).toBeNull()
  })
})
