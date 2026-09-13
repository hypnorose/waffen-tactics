// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, createElement, useEffect } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { useCombatPresentation } from '../combat/useCombatPresentation'
import { ProjectileProvider } from '../useProjectileSystem'
import type { CombatEvent } from '../combat/types'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const rangedAnimation = (eventId: string, seq: number, timestamp: number): CombatEvent => ({
  type: 'animation_start',
  event_id: eventId,
  seq,
  timestamp,
  animation_id: 'ranged_projectile',
  attacker_id: 'player_0',
  target_id: 'opp_0',
})

describe('useCombatPresentation', () => {
  let root: Root | null = null

  beforeEach(() => {
    vi.spyOn(window, 'matchMedia').mockReturnValue({
      matches: false,
      media: '(prefers-reduced-motion: reduce)',
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    } as unknown as MediaQueryList)
  })

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
    vi.restoreAllMocks()
  })

  it('spawns one ranged projectile and one pending visual for duplicate animation aliases', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    const events = [
      rangedAnimation('combat:ranged-1', 20, 4),
      rangedAnimation('combat:ranged-2', 21, 4.04),
    ]

    function Harness() {
      const { recordEvent, activeTracks, pendingVisuals } = useCombatPresentation({
        currentTime: 4,
        replayPaused: false,
      })

      useEffect(() => {
        events.forEach(recordEvent)
      }, [recordEvent])

      return createElement('output', {
        'data-projectile-track-count': activeTracks.filter((track) => track.intent === 'ranged_projectile').length,
        'data-pending-visuals': pendingVisuals,
      })
    }

    act(() => {
      root = createRoot(container)
      root.render(createElement(ProjectileProvider, null, createElement(Harness)))
    })

    expect(container.querySelector('output')?.getAttribute('data-projectile-track-count')).toBe('1')
    expect(container.querySelector('output')?.getAttribute('data-pending-visuals')).toBe('1')
  })
})
