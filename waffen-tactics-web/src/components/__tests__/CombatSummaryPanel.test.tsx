// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import CombatSummaryPanel from '../CombatSummaryPanel'
import { createCombatSummary } from '../../hooks/combat/combatPresentation'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('CombatSummaryPanel', () => {
  let root: Root | null = null

  afterEach(() => {
    if (root) {
      act(() => root?.unmount())
      root = null
    }
    document.body.replaceChildren()
  })

  it('does not present Tempo or a bonus-attack counter', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    const summary = createCombatSummary()
    summary.bonusAttacks = 3

    act(() => {
      root = createRoot(container)
      root.render(<CombatSummaryPanel summary={summary} synergies={{}} />)
    })

    expect(container.textContent).toContain('Podsumowanie walki')
    expect(container.textContent).not.toContain('Tempo')
    expect(container.textContent).not.toContain('bonus attacks')
    expect(container.textContent).not.toContain('x bonus')
  })

  it('shows a readable first-death time without exposing the event sequence', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    const summary = createCombatSummary()
    summary.firstDeath = {
      unit_id: 'opp_0',
      unit_name: 'Pepe',
      timestamp: 0,
      seq: 242,
    }

    act(() => {
      root = createRoot(container)
      root.render(<CombatSummaryPanel summary={summary} synergies={{}} />)
    })

    expect(container.textContent).toContain('Pepe')
    expect(container.textContent).toContain('Czas walki: 0.00s')
    expect(container.textContent).not.toContain('seq')
    expect(container.textContent).not.toContain('242')
  })
})
