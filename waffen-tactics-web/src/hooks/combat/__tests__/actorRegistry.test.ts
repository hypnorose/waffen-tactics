import { describe, expect, it } from 'vitest'
import { createCombatActorRegistry } from '../actorRegistry'

describe('combat actor registry', () => {
  it('keeps canonical ids stable across independent actor replacements', () => {
    const registry = createCombatActorRegistry()
    const playerAnchor = document.createElement('div')
    const opponentAnchor = document.createElement('div')
    const replacementAnchor = document.createElement('div')

    const staleCleanup = registry.register('player_0', playerAnchor)
    registry.register('opp_0', opponentAnchor)
    registry.register('player_0', replacementAnchor)

    expect(registry.getAnchor('player_0')).toBe(replacementAnchor)
    expect(registry.getAnchor('opp_0')).toBe(opponentAnchor)

    staleCleanup()

    expect(registry.getAnchor('player_0')).toBe(replacementAnchor)
    expect(registry.getAnchor('opp_0')).toBe(opponentAnchor)
  })

  it('removes the current anchor only when its own disposer runs', () => {
    const registry = createCombatActorRegistry()
    const anchor = document.createElement('div')
    const cleanup = registry.register('player_0', anchor)

    expect(registry.getAnchor('player_0')).toBe(anchor)
    cleanup()
    expect(registry.getAnchor('player_0')).toBeNull()
  })

  it('ignores blank ids and null anchors without creating a lookup entry', () => {
    const registry = createCombatActorRegistry()

    registry.register('   ', document.createElement('div'))
    registry.register('player_0', null)

    expect(registry.getAnchor('   ')).toBeNull()
    expect(registry.getAnchor('player_0')).toBeNull()
  })
})
