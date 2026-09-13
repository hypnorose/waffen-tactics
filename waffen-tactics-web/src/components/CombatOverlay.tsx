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
import CombatWindowStatusOverlays from './CombatWindowStatusOverlays'

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

      <CombatWindowStatusOverlays
        combatError={combatError}
        showMatchmakingOverlay={showMatchmakingOverlay}
        matchmakingPhase={matchmakingPhase}
        rouletteCandidate={rouletteCandidates[rouletteIndex]}
        showVictoryOverlay={showVictoryOverlay}
        victory={victory}
        defeatMessage={defeatMessage}
      />
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
