import CombatLog from './CombatLog'
import { CombatLogModalProps } from './CombatOverlayTypes'

export default function CombatLogModal({ showLog, visible = true, setShowLog, combatLog, logEndRef }: CombatLogModalProps) {
  if (!showLog) return null

  return (
    <div
      id="combat-log-modal"
      className="combat-log-modal"
      data-visible={visible}
      role="dialog"
      aria-labelledby="combat-log-modal-title"
      aria-hidden={!visible}
    >
      <div className="combat-log-modal-header">
        <span id="combat-log-modal-title">Log walki</span>
        <button className="combat-log-close" aria-label="Close combat log" onClick={() => setShowLog(false)}>×</button>
      </div>
      <div className="combat-log-modal-content">
        <CombatLog combatLog={combatLog} logEndRef={logEndRef} />
      </div>
    </div>
  )
}
