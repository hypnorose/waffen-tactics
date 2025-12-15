import CombatLog from './CombatLog'
import { CombatLogModalProps } from './CombatOverlayTypes'

export default function CombatLogModal({ showLog, setShowLog, combatLog, logEndRef }: CombatLogModalProps) {
  if (!showLog) return null

  return (
    <div style={{ position: 'fixed', top: 80, right: 40, width: 480, height: 500, background: '#0f172a', border: '2px solid #475569', borderRadius: 12, zIndex: 200, boxShadow: '0 8px 32px rgba(0,0,0,0.7)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '0.5rem 1rem', borderBottom: '1px solid #334155', color: '#fbbf24', fontWeight: 700, fontSize: 18 }}>Log walki</div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <CombatLog combatLog={combatLog} logEndRef={logEndRef} />
      </div>
    </div>
  )
}