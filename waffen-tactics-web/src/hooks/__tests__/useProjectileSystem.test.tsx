// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, createElement, useEffect } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { ProjectileProvider, useProjectileSystem } from '../useProjectileSystem'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('useProjectileSystem', () => {
  let root: Root | null = null

  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
    vi.useRealTimers()
  })

  it('keeps one projectile when the same canonical id is requested twice', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)

    function Harness() {
      const { projectiles, spawnProjectile } = useProjectileSystem()

      useEffect(() => {
        spawnProjectile({ id: 'projectile:event-1', fromId: 'player_0', toId: 'opp_0' })
        spawnProjectile({ id: 'projectile:event-1', fromId: 'player_0', toId: 'opp_0' })
      }, [spawnProjectile])

      return createElement('output', { 'data-projectile-count': projectiles.length })
    }

    act(() => {
      root = createRoot(container)
      root.render(createElement(ProjectileProvider, null, createElement(Harness)))
    })

    expect(container.querySelector('output')?.getAttribute('data-projectile-count')).toBe('1')
  })
})
