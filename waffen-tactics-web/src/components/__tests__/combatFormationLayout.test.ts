import { describe, expect, it } from 'vitest'
import { FORMATION_SLOT_COUNT, getFormationSlots } from '../CombatFormationRow'

describe('combat formation slot layout', () => {
  it('reserves the canonical five slots for a partial row', () => {
    const units = [{ id: 'front-0' }, { id: 'front-1' }]
    const slots = getFormationSlots(units)

    expect(FORMATION_SLOT_COUNT).toBe(5)
    expect(slots).toHaveLength(5)
    expect(slots.slice(0, 2)).toEqual(units)
    expect(slots.slice(2)).toEqual([null, null, null])
  })

  it('expands in full row increments without changing unit order', () => {
    const units = Array.from({ length: 6 }, (_, index) => ({ id: `unit-${index}` }))
    const slots = getFormationSlots(units)

    expect(slots).toHaveLength(10)
    expect(slots.slice(0, 6)).toEqual(units)
    expect(slots.slice(6)).toEqual([null, null, null, null])
  })

  it('does not mutate the canonical unit array', () => {
    const units = [{ id: 'unit-0' }]
    getFormationSlots(units)

    expect(units).toEqual([{ id: 'unit-0' }])
  })
})
