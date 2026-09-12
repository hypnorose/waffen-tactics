import { describe, expect, it } from 'vitest'
import { getCombatActionQueueEntries } from '../CombatActionQueue'

describe('getCombatActionQueueEntries', () => {
  it('keeps canonical order and marks bonus attacks without changing event data', () => {
    const entries = getCombatActionQueueEntries([
      { type: 'mana_update', event_id: 'combat:1', seq: 1 },
      { type: 'unit_attack', event_id: 'combat:2', seq: 2, bonus_attack: true, attacker_name: 'A', target_name: 'B' },
      { type: 'unit_died', event_id: 'combat:3', seq: 3, unit_name: 'B' },
    ], 1)

    expect(entries).toEqual([
      { index: 1, eventId: 'combat:2', label: 'BONUS ATTACK', detail: 'A → B' },
      { index: 2, eventId: 'combat:3', label: 'DEATH', detail: 'B' },
    ])
  })

  it('uses only explicit canonical identity and bounds the visible window', () => {
    const events = Array.from({ length: 8 }, (_, index) => ({ type: 'effect_applied', seq: index + 1, unit_id: `unit-${index}` }))
    const entries = getCombatActionQueueEntries(events, 4, 3)

    expect(entries.map((entry) => entry.index)).toEqual([4, 5, 6])
    expect(entries[0].detail).toBe('unit-4')
    expect(getCombatActionQueueEntries([{ type: 'unit_attack', damage: 20 }], 0)[0].eventId).toBe('unit_attack:0')
  })

  it('does not create a queue entry for an empty replay', () => {
    expect(getCombatActionQueueEntries([], 0)).toEqual([])
  })

  it('keeps every explicit multi-hit target visible in the queue detail', () => {
    const [entry] = getCombatActionQueueEntries([{
      type: 'multi_hit',
      event_id: 'combat:multi-hit',
      target_ids: ['opp_0', 'player_0'],
    }], 0)

    expect(entry).toMatchObject({ label: 'MULTI-HIT', detail: 'opp_0 → player_0' })
  })
})
