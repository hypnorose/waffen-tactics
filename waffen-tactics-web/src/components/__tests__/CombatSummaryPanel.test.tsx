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
    expect(container.textContent).not.toContain('Fokus')
    expect(container.textContent).not.toContain('normal target selection')
    expect(container.textContent).not.toContain('bonus attack ready')
    expect(container.textContent).not.toContain('Tempo')
    expect(container.textContent).not.toContain('bonus attacks')
    expect(container.textContent).not.toContain('x bonus')
    expect(container.textContent).toContain('Brak zarejestrowanych obrażeń')
    expect(container.textContent).toContain('Brak danych do porównania')
  })

  it('explains the attack-damage scope and formats a unique leader', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    const summary = createCombatSummary()
    summary.totalDamageByUnit = {
      unit_a: { unit_name: 'Unit A', damage: 100 },
      unit_b: { unit_name: 'Unit B', damage: 50 },
    }

    act(() => {
      root = createRoot(container)
      root.render(<CombatSummaryPanel summary={summary} synergies={{}} />)
    })

    expect(container.textContent).toContain('Najwięcej obrażeń')
    expect(container.textContent).toContain('Unit A — 100 obrażeń')
    expect(container.textContent).toContain('67% obrażeń z ataków w tej walce (łącznie 150 obrażeń)')
    expect(container.textContent).not.toContain('z calosci')
    expect(container.textContent).not.toContain('dmg')
  })

  it('shows a tie instead of choosing one damage leader arbitrarily', () => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    const summary = createCombatSummary()
    summary.totalDamageByUnit = {
      unit_a: { unit_name: 'Unit A', damage: 100 },
      unit_b: { unit_name: 'Unit B', damage: 100 },
    }

    act(() => {
      root = createRoot(container)
      root.render(<CombatSummaryPanel summary={summary} synergies={{}} />)
    })

    expect(container.textContent).toContain('Remis obrażeń')
    expect(container.textContent).toContain('Unit A i Unit B — 100 obrażeń')
    expect(container.textContent).toContain('50% obrażeń z ataków w tej walce (łącznie 200 obrażeń)')
    expect(container.textContent).not.toContain('Najwięcej obrażeń')
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
