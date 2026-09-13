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

const PlayerUnits = memo(function PlayerUnits({ units, regenMap, activeAttackerId, activeTargetId, currentTime, presentationTracks = [], replayPaused = false, reducedMotion = false }: Props) {
  const frontUnits = units.filter(u => u.position === 'front')
  const backUnits = units.filter(u => u.position === 'back')
  return (
    <div className="combat-units-panel bg-gray-800 rounded-lg p-3 border border-gray-700" style={{ flexShrink: 0, width: '100%' }}>
      <h3 className="text-sm font-bold text-green-400 mb-2 text-center">🛡️ Twoje Jednostki</h3>
      
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
          replayPaused={replayPaused}
          reducedMotion={reducedMotion}
        />
      )}
    </div>
  )
})

export default PlayerUnits
