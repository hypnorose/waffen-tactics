import { memo } from 'react'
import CombatFormationRow from './CombatFormationRow'
import type { PresentationTrack } from '../hooks/combat/animation/presentationTimeline'
import type { CombatEvent, TraitDefinition } from '../hooks/combat/types'

interface Props {
  units: any[]
  regenMap: Record<string, any>
  activeAttackerId?: string | null
  activeTargetId?: string | null
  currentTime?: number
  presentationTracks?: PresentationTrack[]
  synergies?: Record<string, { count: number; tier: number }>
  traits?: TraitDefinition[]
  replayEvents?: CombatEvent[]
  replayPaused?: boolean
  reducedMotion?: boolean
}

const OpponentUnits = memo(function OpponentUnits({ units, regenMap, activeAttackerId, activeTargetId, currentTime, presentationTracks = [], synergies = {}, traits = [], replayEvents = [], replayPaused = false, reducedMotion = false }: Props) {
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
          synergies={synergies}
          traits={traits}
          replayEvents={replayEvents}
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
          synergies={synergies}
          traits={traits}
          replayEvents={replayEvents}
          replayPaused={replayPaused}
          reducedMotion={reducedMotion}
        />
      )}
    </section>
  )
})

export default OpponentUnits
