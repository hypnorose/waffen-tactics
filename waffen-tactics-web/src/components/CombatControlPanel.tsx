import type { CombatEvent, CombatSummary, TraitDefinition } from '../hooks/combat/types'
import CombatHeader from './CombatHeader'
import CombatSummaryPanel from './CombatSummaryPanel'
import CombatActionQueue from './CombatActionQueue'
import SynergiesPanel from './SynergiesPanel'
import CombatSpeedPresets from './CombatSpeedPresets'
import { combatOverlaySidebarStyle } from './combatOverlayLayout'

export interface CombatGoldBreakdown {
  base: number
  interest: number
  milestone: number
  win_bonus: number
  total: number
  item_parts: string[]
}

interface Props {
  expanded: boolean
  opponentInfo: { name: string; wins: number; level: number; avatar?: string } | null
  combatSummary?: CombatSummary | null
  synergies: Record<string, { count: number; tier: number }>
  traits: TraitDefinition[]
  replayEvents: CombatEvent[]
  replayEventIndex: number
  combatSpeed: number
  setCombatSpeed: (speed: number) => void
  isFinished: boolean
  storedGoldBreakdown: CombatGoldBreakdown | null
  displayedGoldBreakdown: CombatGoldBreakdown | null
  setDisplayedGoldBreakdown: (breakdown: CombatGoldBreakdown | null) => void
  onContinue: () => void
}

/**
 * Presentation-only owner for the optional combat sidebar. It receives
 * canonical replay projections and emits UI callbacks; it does not own combat
 * rules, replay reduction, or transport state.
 */
export default function CombatControlPanel({
  expanded,
  opponentInfo,
  combatSummary,
  synergies,
  traits,
  replayEvents,
  replayEventIndex,
  combatSpeed,
  setCombatSpeed,
  isFinished,
  storedGoldBreakdown,
  displayedGoldBreakdown,
  setDisplayedGoldBreakdown,
  onContinue,
}: Props) {
  return (
    <div
      className="combat-control-panel"
      id="combat-control-panel"
      aria-hidden={!expanded}
      style={{ ...combatOverlaySidebarStyle, display: expanded ? 'flex' : 'none' }}
    >
      <div>
        <CombatHeader opponentInfo={opponentInfo} />
        <CombatSummaryPanel summary={combatSummary} synergies={synergies} />
        <CombatActionQueue events={replayEvents} currentIndex={replayEventIndex} />
        <details style={{ marginTop: 12, marginBottom: 12 }}>
          <summary style={{ cursor: 'pointer', color: '#cbd5e1', fontSize: 12, fontWeight: 700, listStyle: 'none' }}>
            Pokaż synergie
          </summary>
          <div style={{ marginTop: 8 }}>
            <SynergiesPanel synergies={synergies} traits={traits} />
          </div>
        </details>
        {isFinished && (
          <button
            onClick={() => {
              if (storedGoldBreakdown && !displayedGoldBreakdown) {
                setDisplayedGoldBreakdown(storedGoldBreakdown)
                return
              }
              onContinue()
            }}
            style={{ width: '100%', background: 'linear-gradient(to right, #2563eb, #3b82f6)', color: 'white', fontWeight: 'bold', padding: '12px 24px', borderRadius: 8, border: 'none', cursor: 'pointer', marginTop: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.2)', transition: 'all 0.2s' }}
            onMouseOver={(event) => (event.currentTarget.style.transform = 'scale(1.05)')}
            onMouseOut={(event) => (event.currentTarget.style.transform = 'scale(1)')}
          >
            Kontynuuj
          </button>
        )}
      </div>
      <CombatSpeedPresets combatSpeed={combatSpeed} setCombatSpeed={setCombatSpeed} />
    </div>
  )
}
