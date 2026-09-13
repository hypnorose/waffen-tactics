import { memo } from 'react'
import CombatFormationRow from './CombatFormationRow'
import type { PresentationTrack } from '../hooks/combat/animation/presentationTimeline'

interface Props {
  units: any[]
  regenMap: Record<string, any>
  activeAttackerId?: string | null
  activeTargetId?: string | null
  currentTime?: number
  presentationTracks?: PresentationTrack[]
  replayPaused?: boolean
  reducedMotion?: boolean
}

const OpponentUnits = memo(function OpponentUnits({ units, regenMap, activeAttackerId, activeTargetId, currentTime, presentationTracks = [], replayPaused = false, reducedMotion = false }: Props) {
  const frontUnits = units.filter(u => u.position === 'front')
  const backUnits = units.filter(u => u.position === 'back')

  return (
    <section className="combat-units-panel combat-units-panel-opponent" aria-label="Opponent units">
      <div className="combat-units-panel-heading">
        <div>
          <span className="combat-units-panel-kicker">OPPONENT</span>
          <h3>Przeciwnik</h3>
        </div>
        <span className="combat-units-panel-count">{units.filter(u => u.hp > 0).length}/{units.length}</span>
      </div>
      
      {/* Back Line (now displayed first) */}
      {backUnits.length > 0 && (
        <CombatFormationRow
          units={backUnits}
          isOpponent
          label="Linia Tylna"
          rowName="back"
          regenMap={regenMap}
          activeAttackerId={activeAttackerId}
          activeTargetId={activeTargetId}
          currentTime={currentTime}
          presentationTracks={presentationTracks}
          replayPaused={replayPaused}
          reducedMotion={reducedMotion}
        />
      )}

      {/* Front Line (now displayed second) */}
      {frontUnits.length > 0 && (
        <CombatFormationRow
          units={frontUnits}
          isOpponent
          label="Linia Frontowa"
          rowName="front"
          regenMap={regenMap}
          activeAttackerId={activeAttackerId}
          activeTargetId={activeTargetId}
          currentTime={currentTime}
          presentationTracks={presentationTracks}
          replayPaused={replayPaused}
          reducedMotion={reducedMotion}
        />
      )}
    </section>
  )
})

export default OpponentUnits
