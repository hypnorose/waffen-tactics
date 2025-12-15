import { useRef } from 'react'
import { useCombatOverlayLogic } from '../hooks/useCombatOverlayLogic'
import { PlayerState } from '../store/gameStore'
import GoldNotification from './GoldNotification'
import CombatHeader from './CombatHeader'
import PlayerUnits from './PlayerUnits'
import OpponentUnits from './OpponentUnits'
import CombatLog from './CombatLog'
import CombatFooter from './CombatFooter'
import SynergiesPanel from './SynergiesPanel'
import CombatSpeedSlider from './CombatSpeedSlider'
import CombatLogModal from './CombatLogModal'
import { CombatOverlayProps } from './CombatOverlayTypes'

export default function CombatOverlay({ onClose }: CombatOverlayProps) {
  const logEndRef = useRef<HTMLDivElement>(null)
  const {
    playerUnits,
    opponentUnits,
    combatLog,
    isFinished,
    finalState,
    synergies,
    traits,
    hoveredTrait,
    setHoveredTrait,
    opponentInfo,
    showLog,
    setShowLog,
    attackingUnits,
    targetUnits,
    combatSpeed,
    setCombatSpeed,
    regenMap,
    storedGoldBreakdown,
    displayedGoldBreakdown,
    setDisplayedGoldBreakdown,
    setStoredGoldBreakdown,
    handleClose,
    handleGoldDismiss
  } = useCombatOverlayLogic({ onClose, logEndRef })

  return (
    <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.95)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
      <div style={{ backgroundColor: '#1e293b', borderRadius: '0.75rem', width: '1400px', height: '850px', display: 'flex', flexDirection: 'row', border: '3px solid #475569', boxShadow: '0 20px 60px rgba(0,0,0,0.5)' }}>
        {/* Lewa kolumna */}
        <div style={{ width: 320, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '1.5rem 1rem', borderRight: '2px solid #334155', background: 'rgba(30,41,59,0.98)' }}>
          <div>
            <CombatHeader opponentInfo={opponentInfo} />
            <SynergiesPanel synergies={synergies} traits={traits} hoveredTrait={hoveredTrait} setHoveredTrait={setHoveredTrait} />
          </div>
        </div>

        {/* Prawa szeroka kolumna */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '1.5rem', position: 'relative' }}>
          {/* Jednostki przeciwnika */}
          <div style={{ flex: 1, marginBottom: 16, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start' }}>
            <div className="text-xs text-gray-400 mb-1">Jednostki przeciwnika</div>
            <OpponentUnits units={opponentUnits} attackingUnits={attackingUnits} targetUnits={targetUnits} regenMap={regenMap} />
          </div>
          {/* Jednostki gracza */}
          <div style={{ flex: 1, marginTop: 16, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end' }}>
            <div className="text-xs text-gray-400 mb-1">Twoje jednostki</div>
            <PlayerUnits units={playerUnits} attackingUnits={attackingUnits} targetUnits={targetUnits} regenMap={regenMap} />
          </div>

          {/* Przycisk do logu walki */}
          <button onClick={() => setShowLog(!showLog)} style={{ position: 'absolute', top: 16, right: 16, zIndex: 100, background: '#334155', color: '#fbbf24', border: 'none', borderRadius: 6, padding: '6px 16px', fontWeight: 600, cursor: 'pointer', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}>
            {showLog ? 'Ukryj log walki' : 'Pokaż log walki'}
          </button>

          {/* Slider prędkości walki pod planszą */}
          <CombatSpeedSlider combatSpeed={combatSpeed} setCombatSpeed={setCombatSpeed} />

          {/* Log walki jako modal */}
          <CombatLogModal showLog={showLog} setShowLog={setShowLog} combatLog={combatLog} logEndRef={logEndRef} />

          {/* Footer z przyciskiem kontynuacji */}
          <div style={{ marginTop: 24 }}>
            <CombatFooter isFinished={isFinished} storedGoldBreakdown={storedGoldBreakdown} displayedGoldBreakdown={displayedGoldBreakdown} handleClose={handleClose} handleGoldDismiss={handleGoldDismiss} setDisplayedGoldBreakdown={setDisplayedGoldBreakdown} />
          </div>
        </div>
      </div>

      {/* Gold Notification Overlay */}
      <GoldNotification breakdown={displayedGoldBreakdown} onDismiss={handleGoldDismiss} />
    </div>
  )
}

