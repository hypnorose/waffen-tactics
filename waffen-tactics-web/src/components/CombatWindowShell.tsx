import type { ReactNode } from 'react'
import { combatOverlayBoardStyle, combatOverlayPanelStyle } from './combatOverlayLayout'

interface CombatWindowShellProps {
  expanded: boolean
  showLog: boolean
  combatPanel: ReactNode
  opponentSlot: ReactNode
  playerSlot: ReactNode
  log: ReactNode
  replayControls: ReactNode
  onTogglePanel: () => void
  onToggleLog: () => void
}

/**
 * Presentation-only owner for the combat window frame. The shell arranges
 * stable arena slots and optional controls; combat state and replay decisions
 * stay in the hook and the supplied child components.
 */
export default function CombatWindowShell({
  expanded,
  showLog,
  combatPanel,
  opponentSlot,
  playerSlot,
  log,
  replayControls,
  onTogglePanel,
  onToggleLog,
}: CombatWindowShellProps) {
  return (
    <div className="combat-overlay-panel" style={combatOverlayPanelStyle}>
      {combatPanel}

      <main className="combat-overlay-board" style={combatOverlayBoardStyle}>
        <div className="combat-arena-brand" aria-label="Waffen Tactics Set 2 Świt Nowociot">
          <span>WAFFEN TACTICS</span>
          <strong>SET 2: ŚWIT NOWOCIOT</strong>
        </div>

        <div className="combat-opponent-slot">
          {opponentSlot}
        </div>

        <div className="combat-arena-divider" aria-hidden="true">
          <span>VS</span>
        </div>

        <div className="combat-player-slot">
          {playerSlot}
        </div>

        <button
          type="button"
          className="combat-panel-toggle"
          aria-controls="combat-control-panel"
          aria-expanded={expanded}
          aria-label={expanded ? 'Zwiń panel walki' : 'Rozwiń panel walki'}
          onClick={onTogglePanel}
        >
          {expanded ? 'Zwiń panel' : 'Rozwiń panel'}
        </button>

        <button
          type="button"
          className="combat-log-toggle"
          aria-controls="combat-log-modal"
          aria-expanded={showLog}
          aria-label={showLog ? 'Hide combat log' : 'Show combat log'}
          onClick={onToggleLog}
        >
          {showLog && expanded ? 'Ukryj log walki' : 'Pokaż log walki'}
        </button>

        {log}
        {replayControls}
      </main>
    </div>
  )
}
