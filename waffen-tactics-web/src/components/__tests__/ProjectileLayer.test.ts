import { describe, expect, it } from 'vitest'
import { resolveProjectileEndpoints } from '../ProjectileLayer'

describe('ProjectileLayer endpoint contract', () => {
  it('fails closed when either visual actor anchor is missing', () => {
    const getCenter = (id: string) => id === 'player_0' ? { x: 10, y: 20 } : null

    expect(resolveProjectileEndpoints(getCenter, { fromId: 'player_0', toId: 'opp_0' }, null)).toBeNull()
  })

  it('resolves both endpoints from the registered anchors', () => {
    const getCenter = (id: string) => id === 'player_0'
      ? { x: 10, y: 20 }
      : { x: 100, y: 200 }

    expect(resolveProjectileEndpoints(getCenter, { fromId: 'player_0', toId: 'opp_0' }, null)).toEqual({
      start: { x: 10, y: 20 },
      end: { x: 100, y: 200 },
    })
  })
})
