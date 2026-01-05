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
import DesyncInspector from './DesyncInspector'
import { CombatOverlayProps } from './CombatOverlayTypes'
import { UnitAnchorsProvider } from '../hooks/useUnitAnchors'
import { ProjectileProvider } from '../hooks/useProjectileSystem'
import ProjectileLayer from './ProjectileLayer'

function CombatOverlayContent({ onClose }: CombatOverlayProps) {
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
    combatSpeed,
    setCombatSpeed,
    regenMap,
    storedGoldBreakdown,
    displayedGoldBreakdown,
    setDisplayedGoldBreakdown,
    setStoredGoldBreakdown,
    handleClose,
    handleGoldDismiss,
    defeatMessage,
    desyncLogs,
    clearDesyncLogs,
    exportDesyncJSON
  } = useCombatOverlayLogic({ onClose, logEndRef })
  const [showDesyncInspector, setShowDesyncInspector] = useState(false)

  useEffect(() => {
    if (victory !== null && isFinished) {
      const showTimer = setTimeout(() => setShowVictoryOverlay(true), 500)
      const hideTimer = setTimeout(() => setShowVictoryOverlay(false), 2100)
      return () => { clearTimeout(showTimer); clearTimeout(hideTimer) }
    } else {
      setShowVictoryOverlay(false)
    }
  }, [victory, isFinished])

  return (
    <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.95)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
      <div style={{ backgroundColor: '#1e293b', borderRadius: '0.75rem', width: '1400px', height: '850px', display: 'flex', flexDirection: 'row', border: '3px solid #475569', boxShadow: '0 20px 60px rgba(0,0,0,0.5)' }}>
        <div style={{ width: 320, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '1.5rem 1rem', borderRight: '2px solid #334155', background: 'rgba(30,41,59,0.98)' }}>
          <div>
            <CombatHeader opponentInfo={opponentInfo} />
            <SynergiesPanel synergies={synergies} traits={traits} hoveredTrait={hoveredTrait} setHoveredTrait={setHoveredTrait} />
            {isFinished && (
              <button
                onClick={() => {
                  if (storedGoldBreakdown && !displayedGoldBreakdown) {
                    setDisplayedGoldBreakdown(storedGoldBreakdown)
                    return
                  }
                  handleClose()
                }}
                style={{ width: '100%', background: 'linear-gradient(to right, #2563eb, #3b82f6)', color: 'white', fontWeight: 'bold', padding: '12px 24px', borderRadius: 8, border: 'none', cursor: 'pointer', marginTop: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.2)', transition: 'all 0.2s' }}
                onMouseOver={(e) => (e.currentTarget.style.transform = 'scale(1.05)')}
                onMouseOut={(e) => (e.currentTarget.style.transform = 'scale(1)')}
              >
                Kontynuuj
              </button>
            )}
          </div>
          <CombatSpeedSlider combatSpeed={combatSpeed} setCombatSpeed={setCombatSpeed} />
        </div>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '1.5rem', position: 'relative' }}>
          <div style={{ flex: 1, marginBottom: 16, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start' }}>
            <OpponentUnits units={opponentUnits} regenMap={regenMap} />
          </div>
          <div style={{ flex: 1, marginTop: 16, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end' }}>
            <PlayerUnits units={playerUnits} regenMap={regenMap} />
          </div>

          <button onClick={() => setShowLog(!showLog)} style={{ position: 'absolute', top: 16, right: 16, zIndex: 100, background: '#334155', color: '#fbbf24', border: 'none', borderRadius: 6, padding: '6px 16px', fontWeight: 600, cursor: 'pointer', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}>
            {showLog ? 'Ukryj log walki' : 'Pokaż log walki'}
          </button>

          {import.meta.env.DEV && (
            <button onClick={() => setShowDesyncInspector((s) => !s)} style={{ position: 'absolute', top: 56, right: 16, zIndex: 100, background: '#1f2937', color: '#7dd3fc', border: 'none', borderRadius: 6, padding: '6px 12px', fontWeight: 600, cursor: 'pointer', boxShadow: '0 2px 8px rgba(0,0,0,0.12)' }}>
              {showDesyncInspector ? 'Ukryj Desync Inspector' : 'Pokaż Desync Inspector'}
            </button>
          )}

          <CombatLogModal showLog={showLog} setShowLog={setShowLog} combatLog={combatLog} logEndRef={logEndRef} />
        </div>
      </div>

      <ProjectileLayer />
      <GoldNotification breakdown={displayedGoldBreakdown} onDismiss={handleGoldDismiss} />
      {import.meta.env.DEV && showDesyncInspector && <DesyncInspector desyncLogs={(desyncLogs as any) || []} onClear={(clearDesyncLogs as any) || (() => {})} onExport={(exportDesyncJSON as any) || (() => '[]')} />}

      <div className={`absolute inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-60 transition-all duration-300 ease-out ${showVictoryOverlay ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'}`}>
        <div className="bg-surface border-4 border-primary/60 rounded-xl p-8 shadow-2xl">
          <div className={`text-5xl font-bold text-center ${victory ? 'text-green-400' : 'text-red-400'}`}>
            {victory ? '🎉 ZWYCIĘSTWO! 🎉' : defeatMessage || '💔 PRZEGRANA! 💔'}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function CombatOverlay({ onClose }: CombatOverlayProps) {
  return (
    <UnitAnchorsProvider>
      <ProjectileProvider>
        <CombatOverlayContent onClose={onClose} />
      </ProjectileProvider>
    </UnitAnchorsProvider>
  )
}

