import { useRef, useState, useEffect } from 'react'
import { useCombatOverlayLogic } from '../hooks/useCombatOverlayLogic'
import { PlayerState } from '../store/gameStore'
import GoldNotification from './GoldNotification'
import CombatHeader from './CombatHeader'
import PlayerUnits from './PlayerUnits'
import OpponentUnits from './OpponentUnits'
import CombatLog from './CombatLog'
// import CombatFooter from './CombatFooter'
import CombatSummaryPanel from './CombatSummaryPanel'
import SynergiesPanel from './SynergiesPanel'
import CombatSpeedSlider from './CombatSpeedSlider'
import CombatLogModal from './CombatLogModal'
import DesyncInspector from './DesyncInspector'
import ReplayControls from './ReplayControls'
import { CombatOverlayProps } from './CombatOverlayTypes'
import { UnitAnchorsProvider } from '../hooks/useUnitAnchors'
import { ProjectileProvider } from '../hooks/useProjectileSystem'
import ProjectileLayer from './ProjectileLayer'
import { combatOverlayBoardStyle, combatOverlayPanelStyle, combatOverlaySidebarStyle, shouldStartCombatPanelCollapsed } from './combatOverlayLayout'

export function CombatOverlayContent({ onClose }: CombatOverlayProps) {
  const logEndRef = useRef<HTMLDivElement>(null)
  const [showVictoryOverlay, setShowVictoryOverlay] = useState(false)
  const [rouletteIndex, setRouletteIndex] = useState(0)
  const [matchmakingPhase, setMatchmakingPhase] = useState<'searching' | 'final' | 'done'>('searching')
  const [replayGateOpen, setReplayGateOpen] = useState(false)
  const [combatPanelExpanded, setCombatPanelExpanded] = useState(() => {
    if (typeof window === 'undefined') return true
    return !shouldStartCombatPanelCollapsed(window.innerWidth)
  })

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
    combatSummary,
    activeAttackerId,
    activeTargetId,
    simTime,
    replayEvents,
    replayEventIndex,
    replayPlaying,
    replaySeekError,
    combatError,
    restartReplay,
    toggleReplay,
    seekReplay,
    desyncLogs,
    clearDesyncLogs,
    exportDesyncJSON
  } = useCombatOverlayLogic({ onClose, logEndRef, replayEnabled: replayGateOpen })
  const [showDesyncInspector, setShowDesyncInspector] = useState(false)

  const rouletteCandidates = [
    'Uszaty Cwel',
    'Słonik Dumbo',
    'Srebrny Baron',
    'Spijacz kropelek',
    'Spermofil pospolity',
    'Przyprawowy Imperator',
    'Giełdowy Dyletant',
    'Obwoźny sprzedawca oprawek',
    'Grochowianin nr. 207',
    'Skurwiel z Wesołej'
  ]

  useEffect(() => {
    if (victory !== null && isFinished) {
      const showTimer = setTimeout(() => setShowVictoryOverlay(true), 500)
      const hideTimer = setTimeout(() => setShowVictoryOverlay(false), 2100)
      return () => { clearTimeout(showTimer); clearTimeout(hideTimer) }
    } else {
      setShowVictoryOverlay(false)
    }
  }, [victory, isFinished])

  useEffect(() => {
    setMatchmakingPhase('searching')
    const rouletteTimer = setTimeout(() => setMatchmakingPhase('final'), 2000)
    const finalTimer = setTimeout(() => setMatchmakingPhase('done'), 3000)
    return () => {
      clearTimeout(rouletteTimer)
      clearTimeout(finalTimer)
    }
  }, [])

  useEffect(() => {
    if (matchmakingPhase !== 'searching') return
    const interval = setInterval(() => {
      setRouletteIndex(prev => (prev + 1) % rouletteCandidates.length)
    }, 320)
    return () => clearInterval(interval)
  }, [matchmakingPhase, rouletteCandidates.length])

  const showMatchmakingOverlay = matchmakingPhase !== 'done'

  useEffect(() => {
    // Replay starts only after matchmaking/intro panel is fully dismissed.
    setReplayGateOpen(!showMatchmakingOverlay)
  }, [showMatchmakingOverlay])

  return (
    <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.95)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
      {!showMatchmakingOverlay && (
        <>
          <div style={combatOverlayPanelStyle}>
            <div
              id="combat-control-panel"
              aria-hidden={!combatPanelExpanded}
              style={{ ...combatOverlaySidebarStyle, display: combatPanelExpanded ? 'flex' : 'none' }}
            >
              <div>
                <CombatHeader opponentInfo={opponentInfo} />
                <CombatSummaryPanel summary={combatSummary} synergies={synergies} />
                <details style={{ marginTop: 12, marginBottom: 12 }}>
                  <summary style={{ cursor: 'pointer', color: '#cbd5e1', fontSize: 12, fontWeight: 700, listStyle: 'none' }}>
                    Pokaż synergie
                  </summary>
                  <div style={{ marginTop: 8 }}>
                    <SynergiesPanel synergies={synergies} traits={traits} hoveredTrait={hoveredTrait} setHoveredTrait={setHoveredTrait} />
                  </div>
                </details>
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

            <div className="combat-overlay-board" style={combatOverlayBoardStyle}>
              <div className="combat-opponent-slot" style={{ flex: 1, marginBottom: 16, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start' }}>
                <OpponentUnits units={opponentUnits} regenMap={regenMap} activeAttackerId={activeAttackerId} activeTargetId={activeTargetId} currentTime={simTime} />
              </div>
              <div className="combat-player-slot" style={{ flex: 1, marginTop: 16, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end' }}>
                <PlayerUnits units={playerUnits} regenMap={regenMap} activeAttackerId={activeAttackerId} activeTargetId={activeTargetId} currentTime={simTime} />
              </div>

              <button
                type="button"
                className="combat-panel-toggle"
                aria-controls="combat-control-panel"
                aria-expanded={combatPanelExpanded}
                aria-label={combatPanelExpanded ? 'Zwiń panel walki' : 'Rozwiń panel walki'}
                onClick={() => setCombatPanelExpanded((expanded) => !expanded)}
                style={{ position: 'absolute', top: 16, left: 16, zIndex: 100, background: '#334155', color: '#fbbf24', border: '1px solid rgba(251,191,36,0.55)', borderRadius: 6, padding: '6px 12px', fontWeight: 700, cursor: 'pointer', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}
              >
                {combatPanelExpanded ? 'Zwiń panel' : 'Rozwiń panel'}
              </button>

              <button type="button" onClick={() => setShowLog(!showLog)} style={{ position: 'absolute', top: 16, right: 16, zIndex: 100, background: '#334155', color: '#fbbf24', border: 'none', borderRadius: 6, padding: '6px 16px', fontWeight: 600, cursor: 'pointer', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}>
                {showLog && combatPanelExpanded ? 'Ukryj log walki' : 'Pokaż log walki'}
              </button>

              {import.meta.env.DEV && (
                <button type="button" onClick={() => setShowDesyncInspector((s) => !s)} style={{ position: 'absolute', top: 56, right: 16, zIndex: 100, background: '#1f2937', color: '#7dd3fc', border: 'none', borderRadius: 6, padding: '6px 12px', fontWeight: 600, cursor: 'pointer', boxShadow: '0 2px 8px rgba(0,0,0,0.12)' }}>
                  {showDesyncInspector ? 'Ukryj Desync Inspector' : 'Pokaż Desync Inspector'}
                </button>
              )}

              <CombatLogModal showLog={showLog} visible={combatPanelExpanded} setShowLog={setShowLog} combatLog={combatLog} logEndRef={logEndRef} />
              <ReplayControls
                eventCount={replayEvents.length}
                currentIndex={replayEventIndex}
                currentEvent={replayEvents[replayEventIndex]}
                isPlaying={replayPlaying}
                error={replaySeekError}
                disabled={Boolean(combatError)}
                onRestart={restartReplay}
                onTogglePlay={toggleReplay}
                onSeek={seekReplay}
                visible={combatPanelExpanded}
              />
            </div>
          </div>

          <ProjectileLayer />
          <GoldNotification breakdown={displayedGoldBreakdown} onDismiss={handleGoldDismiss} />
          {import.meta.env.DEV && showDesyncInspector && <DesyncInspector desyncLogs={(desyncLogs as any) || []} onClear={(clearDesyncLogs as any) || (() => {})} onExport={(exportDesyncJSON as any) || (() => '[]')} />}
        </>
      )}

      {combatError && (
        <div
          role="alert"
          aria-live="assertive"
          style={{
            position: 'fixed',
            left: '50%',
            top: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 100,
            width: 'min(92vw, 460px)',
            padding: 20,
            border: '1px solid rgba(248,113,113,0.8)',
            borderRadius: 12,
            background: 'rgba(69,10,10,0.97)',
            color: '#fee2e2',
            boxShadow: '0 16px 48px rgba(0,0,0,0.5)',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: 18, fontWeight: 800, marginBottom: 8 }}>Walka zatrzymana</div>
          <div style={{ fontSize: 14, lineHeight: 1.45 }}>{combatError.message}</div>
          <div style={{ marginTop: 10, color: '#fecaca', fontSize: 12 }}>
            Kod: <code>{combatError.code}</code>
          </div>
          <div style={{ marginTop: 12, fontSize: 12, color: '#fca5a5' }}>
            {combatError.retriable
              ? 'Spróbuj ponownie po odświeżeniu strony.'
              : 'Odśwież stronę, aby wczytać aktualny stan gry.'}
          </div>
        </div>
      )}

      <div className={`absolute inset-0 bg-slate-950 backdrop-blur-sm flex items-center justify-center z-[65] transition-all duration-300 ${showMatchmakingOverlay ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}>
        <div className="bg-slate-900/90 border border-slate-600 rounded-xl p-8 min-w-[440px] text-center shadow-2xl">
          <div className="flex justify-center mb-5">
            <div className="w-12 h-12 border-4 border-yellow-400/40 border-t-yellow-300 rounded-full animate-spin" />
          </div>
          <div className="text-2xl font-bold text-yellow-200 mb-3">
            {matchmakingPhase === 'searching' ? 'Szukanie przeciwnika...' : 'Znaleziono przeciwnika!'}
          </div>
          <div className="text-lg text-slate-100 font-semibold min-h-[28px] transition-all duration-150">
            {matchmakingPhase === 'searching' ? rouletteCandidates[rouletteIndex] : 'Godny przeciwnik'}
          </div>
        </div>
      </div>

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
