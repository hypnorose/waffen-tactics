import { useRef, useState, useEffect } from 'react'
import { useCombatOverlayLogic } from '../hooks/useCombatOverlayLogic'
import { PlayerState } from '../store/gameStore'
import GoldNotification from './GoldNotification'
import CombatHeader from './CombatHeader'
import PlayerUnits from './PlayerUnits'
import OpponentUnits from './OpponentUnits'
import CombatLog from './CombatLog'
// import CombatFooter from './CombatFooter'
import SynergiesPanel from './SynergiesPanel'
import CombatSpeedSlider from './CombatSpeedSlider'
import CombatLogModal from './CombatLogModal'
import { CombatOverlayProps } from './CombatOverlayTypes'

export default function CombatOverlay({ onClose }: CombatOverlayProps) {
  const logEndRef = useRef<HTMLDivElement>(null)
  const [showVictoryOverlay, setShowVictoryOverlay] = useState(false)

  const {
    playerUnits,
    opponentUnits,
    combatLog,
    isFinished,
    victory,
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

  useEffect(() => {
    if (victory !== null) {
      // Delay appearance for smooth transition
      const showTimer = setTimeout(() => {
        setShowVictoryOverlay(true)
      }, 100)
      
      const hideTimer = setTimeout(() => {
        setShowVictoryOverlay(false)
      }, 2100) // 100ms delay + 2000ms show
      
      return () => {
        clearTimeout(showTimer)
        clearTimeout(hideTimer)
      }
    } else {
      setShowVictoryOverlay(false)
    }
  }, [victory])

  return (
    <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.95)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
      <div style={{ backgroundColor: '#1e293b', borderRadius: '0.75rem', width: '1400px', height: '850px', display: 'flex', flexDirection: 'row', border: '3px solid #475569', boxShadow: '0 20px 60px rgba(0,0,0,0.5)' }}>
        {/* Lewa kolumna */}
        <div style={{ width: 320, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '1.5rem 1rem', borderRight: '2px solid #334155', background: 'rgba(30,41,59,0.98)' }}>
          <div>
            <CombatHeader opponentInfo={opponentInfo} />
            <SynergiesPanel synergies={synergies} traits={traits} hoveredTrait={hoveredTrait} setHoveredTrait={setHoveredTrait} />
            {isFinished && (
              <button onClick={() => { if (storedGoldBreakdown && !displayedGoldBreakdown) { setDisplayedGoldBreakdown(storedGoldBreakdown); return } handleClose() }} style={{ width: '100%', background: 'linear-gradient(to right, #2563eb, #3b82f6)', color: 'white', fontWeight: 'bold', padding: '12px 24px', borderRadius: 8, border: 'none', cursor: 'pointer', marginTop: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.2)', transition: 'all 0.2s' }} onMouseOver={(e) => e.currentTarget.style.transform = 'scale(1.05)'} onMouseOut={(e) => e.currentTarget.style.transform = 'scale(1)'}>
                Kontynuuj
              </button>
            )}
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
          {/* <CombatFooter isFinished={isFinished} storedGoldBreakdown={storedGoldBreakdown} displayedGoldBreakdown={displayedGoldBreakdown} handleClose={handleClose} handleGoldDismiss={handleGoldDismiss} setDisplayedGoldBreakdown={setDisplayedGoldBreakdown} /> */}
        </div>
      </div>

      {/* Gold Notification Overlay */}
      <GoldNotification breakdown={displayedGoldBreakdown} onDismiss={handleGoldDismiss} />

      {/* Victory/Defeat Overlay */}
      <div className={`absolute inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-60 transition-all duration-300 ease-out ${showVictoryOverlay ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'}`}>
        <div className="bg-surface border-4 border-primary/60 rounded-xl p-8 shadow-2xl">
          <div className={`text-5xl font-bold text-center ${victory ? 'text-green-400' : 'text-red-400'}`}>
            {victory ? '🎉 ZWYCIĘSTWO! 🎉' : '💔 PRZEGRANA! 💔'}
          </div>
        </div>
      </div>
    </div>
  )
}

