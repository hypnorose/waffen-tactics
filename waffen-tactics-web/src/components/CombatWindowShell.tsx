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

      <div className="combat-overlay-board" style={combatOverlayBoardStyle}>
        <div
          className="combat-opponent-slot"
          style={{ flex: 1, marginBottom: 16, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start' }}
        >
          {opponentSlot}
        </div>
        <div
          className="combat-player-slot"
          style={{ flex: 1, marginTop: 16, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end' }}
        >
          {playerSlot}
        </div>

        <button
          type="button"
          className="combat-panel-toggle"
          aria-controls="combat-control-panel"
          aria-expanded={expanded}
          aria-label={expanded ? 'Zwiń panel walki' : 'Rozwiń panel walki'}
          onClick={onTogglePanel}
          style={{ position: 'absolute', top: 16, left: 16, zIndex: 100, background: '#334155', color: '#fbbf24', border: '1px solid rgba(251,191,36,0.55)', borderRadius: 6, padding: '6px 12px', fontWeight: 700, cursor: 'pointer', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}
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
          style={{ position: 'absolute', top: 16, right: 16, zIndex: 100, background: '#334155', color: '#fbbf24', border: 'none', borderRadius: 6, padding: '6px 16px', fontWeight: 600, cursor: 'pointer', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}
        >
          {showLog && expanded ? 'Ukryj log walki' : 'Pokaż log walki'}
        </button>

        {log}
        {replayControls}
      </div>
    </div>
  )
}
