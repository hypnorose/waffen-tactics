import { useRef, useState, useEffect } from 'react'
import { useCombatOverlayLogic } from '../hooks/useCombatOverlayLogic'
import { PlayerState } from '../store/gameStore'
import GoldNotification from './GoldNotification'
import PlayerUnits from './PlayerUnits'
import OpponentUnits from './OpponentUnits'
// import CombatFooter from './CombatFooter'
import CombatLogModal from './CombatLogModal'
import DesyncInspector from './DesyncInspector'
import ReplayControls from './ReplayControls'
import CombatControlPanel from './CombatControlPanel'
import { CombatOverlayProps } from './CombatOverlayTypes'
import { UnitAnchorsProvider } from '../hooks/useUnitAnchors'
import { ProjectileProvider } from '../hooks/useProjectileSystem'
import ProjectileLayer from './ProjectileLayer'
import CombatFeedbackLayer from './CombatFeedbackLayer'
import { shouldStartCombatPanelCollapsed } from './combatOverlayLayout'
import CombatWindowShell from './CombatWindowShell'
import { Panel } from '../ui/primitives'

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
    presentationTracks = [],
    presentationDiagnostics = [],
    reducedMotion = false,
    replayPaused = false,
    reportPresentationDiagnostic = () => {},
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
    <div className="combat-overlay-root" style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.95)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
      {!showMatchmakingOverlay && (
        <>
          <CombatWindowShell
            expanded={combatPanelExpanded}
            showLog={showLog}
            onTogglePanel={() => setCombatPanelExpanded((expanded) => !expanded)}
            onToggleLog={() => setShowLog(!showLog)}
            combatPanel={(
              <CombatControlPanel
                expanded={combatPanelExpanded}
                opponentInfo={opponentInfo}
                combatSummary={combatSummary}
                synergies={synergies}
                traits={traits}
                replayEvents={replayEvents}
                replayEventIndex={replayEventIndex}
                combatSpeed={combatSpeed}
                setCombatSpeed={setCombatSpeed}
                isFinished={isFinished}
                storedGoldBreakdown={storedGoldBreakdown}
                displayedGoldBreakdown={displayedGoldBreakdown}
                setDisplayedGoldBreakdown={setDisplayedGoldBreakdown}
                onContinue={handleClose}
              />
            )}
            opponentSlot={<OpponentUnits units={opponentUnits} regenMap={regenMap} activeAttackerId={activeAttackerId} activeTargetId={activeTargetId} currentTime={simTime} presentationTracks={presentationTracks} replayPaused={replayPaused} reducedMotion={reducedMotion} />}
            playerSlot={<PlayerUnits units={playerUnits} regenMap={regenMap} activeAttackerId={activeAttackerId} activeTargetId={activeTargetId} currentTime={simTime} presentationTracks={presentationTracks} replayPaused={replayPaused} reducedMotion={reducedMotion} />}
            log={<CombatLogModal showLog={showLog} visible={combatPanelExpanded} setShowLog={setShowLog} combatLog={combatLog} logEndRef={logEndRef} />}
            replayControls={(
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
            )}
          />

          <ProjectileLayer onDiagnostic={reportPresentationDiagnostic} />
          <CombatFeedbackLayer
            event={replayEvents[replayEventIndex]}
            eventIndex={replayEventIndex}
            replayPaused={replayPaused}
            reducedMotion={reducedMotion}
          />
          {presentationDiagnostics.length > 0 && (
            <div
              role="status"
              aria-live="polite"
              data-presentation-diagnostics
              style={{ position: 'fixed', left: 16, bottom: 16, zIndex: 220, maxWidth: 'min(92vw, 560px)', padding: '8px 12px', border: '1px solid rgba(248,113,113,0.75)', borderRadius: 8, background: 'rgba(69,10,10,0.94)', color: '#fecaca', fontSize: 12, lineHeight: 1.35, boxShadow: '0 8px 24px rgba(0,0,0,0.35)' }}
            >
              Prezentacja: {presentationDiagnostics[presentationDiagnostics.length - 1].message}
            </div>
          )}
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
        <Panel variant="overlay" className="combat-matchmaking-panel border-slate-600 rounded-xl p-8 min-w-[440px] text-center shadow-2xl">
          <div className="flex justify-center mb-5">
            <div className="w-12 h-12 border-4 border-yellow-400/40 border-t-yellow-300 rounded-full animate-spin" />
          </div>
          <div className="text-2xl font-bold text-yellow-200 mb-3">
            {matchmakingPhase === 'searching' ? 'Szukanie przeciwnika...' : 'Znaleziono przeciwnika!'}
          </div>
          <div className="text-lg text-slate-100 font-semibold min-h-[28px] transition-all duration-150">
            {matchmakingPhase === 'searching' ? rouletteCandidates[rouletteIndex] : 'Godny przeciwnik'}
          </div>
        </Panel>
      </div>

      <div className={`absolute inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-60 transition-all duration-300 ease-out ${showVictoryOverlay ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'}`}>
        <Panel variant="raised" className="combat-victory-panel border-4 border-primary/60 rounded-xl p-8 shadow-2xl">
          <div className={`text-5xl font-bold text-center ${victory ? 'text-green-400' : 'text-red-400'}`}>
            {victory ? '🎉 ZWYCIĘSTWO! 🎉' : defeatMessage || '💔 PRZEGRANA! 💔'}
          </div>
        </Panel>
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
