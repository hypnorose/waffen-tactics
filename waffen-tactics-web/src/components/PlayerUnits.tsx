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

const PlayerUnits = memo(function PlayerUnits({ units, regenMap, activeAttackerId, activeTargetId, currentTime, presentationTracks = [], synergies = {}, traits = [], replayEvents = [], replayPaused = false, reducedMotion = false }: Props) {
  const frontUnits = units.filter(u => u.position === 'front')
  const backUnits = units.filter(u => u.position === 'back')
  return (
    <section className="combat-units-panel combat-units-panel-player" aria-label="Your units">
      <div className="combat-units-panel-heading">
        <div>
          <span className="combat-units-panel-kicker">YOUR SQUAD</span>
          <h3>Twoje jednostki</h3>
        </div>
        <span className="combat-units-panel-count">{units.filter(u => u.hp > 0).length}/{units.length}</span>
      </div>
      
      {/* Front Line */}
      {frontUnits.length > 0 && (
        <CombatFormationRow
          units={frontUnits}
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

      {/* Back Line */}
      {backUnits.length > 0 && (
        <CombatFormationRow
          units={backUnits}
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
    </section>
  )
})

export default PlayerUnits
