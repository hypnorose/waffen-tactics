import { useRef, useState, useEffect } from 'react'
import { useCombatOverlayLogic } from '../hooks/useCombatOverlayLogic'
import { useCombatMatchmakingFlow } from '../hooks/useCombatMatchmakingFlow'
import { PlayerState } from '../store/gameStore'
import GoldNotification from './GoldNotification'
import PlayerUnits from './PlayerUnits'
import OpponentUnits from './OpponentUnits'
// import CombatFooter from './CombatFooter'
import CombatLogModal from './CombatLogModal'
import ReplayControls from './ReplayControls'
import CombatControlPanel from './CombatControlPanel'
import { CombatOverlayProps } from './CombatOverlayTypes'
import { UnitAnchorsProvider } from '../hooks/useUnitAnchors'
import { ProjectileProvider } from '../hooks/useProjectileSystem'
import ProjectileLayer from './ProjectileLayer'
import CombatFeedbackLayer from './CombatFeedbackLayer'
import CombatWindowShell from './CombatWindowShell'
import CombatWindowStatusOverlays from './CombatWindowStatusOverlays'

export function CombatOverlayContent({ onClose }: CombatOverlayProps) {
  const logEndRef = useRef<HTMLDivElement>(null)
  const [showVictoryOverlay, setShowVictoryOverlay] = useState(false)
  const [combatPanelExpanded, setCombatPanelExpanded] = useState(false)
  const {
    matchmakingPhase,
    rouletteCandidate,
    showMatchmakingOverlay,
    replayGateOpen,
  } = useCombatMatchmakingFlow()

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
  } = useCombatOverlayLogic({ onClose, logEndRef, replayEnabled: replayGateOpen })

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
    <div className="combat-overlay-root">
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
            opponentSlot={<OpponentUnits units={opponentUnits} regenMap={regenMap} activeAttackerId={activeAttackerId} activeTargetId={activeTargetId} currentTime={simTime} presentationTracks={presentationTracks} synergies={synergies} traits={traits} replayEvents={replayEvents} replayPaused={replayPaused} reducedMotion={reducedMotion} />}
            playerSlot={<PlayerUnits units={playerUnits} regenMap={regenMap} activeAttackerId={activeAttackerId} activeTargetId={activeTargetId} currentTime={simTime} presentationTracks={presentationTracks} synergies={synergies} traits={traits} replayEvents={replayEvents} replayPaused={replayPaused} reducedMotion={reducedMotion} />}
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
        </>
      )}

      <CombatWindowStatusOverlays
        combatError={combatError}
        showMatchmakingOverlay={showMatchmakingOverlay}
        matchmakingPhase={matchmakingPhase}
        rouletteCandidate={rouletteCandidate}
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
