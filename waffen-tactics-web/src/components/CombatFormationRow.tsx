import { motion } from 'framer-motion'
import CombatUnitCard from './CombatUnitCard'
import type { PresentationTrack } from '../hooks/combat/animation/presentationTimeline'
import type { CombatEvent, TraitDefinition } from '../hooks/combat/types'

export const FORMATION_SLOT_COUNT = 5

/**
 * Keep a formation row's logical capacity stable when a roster is partial.
 * Empty slots are layout-only; they never enter the anchor registry.
 */
export function getFormationSlots<T>(units: T[], minimumSlots = FORMATION_SLOT_COUNT): Array<T | null> {
  const safeMinimum = Math.max(1, Math.floor(minimumSlots))
  const slotCount = Math.max(safeMinimum, Math.ceil(units.length / safeMinimum) * safeMinimum)
  return Array.from({ length: slotCount }, (_, index) => units[index] ?? null)
}

interface Props {
  units: any[]
  isOpponent?: boolean
  label: string
  rowName: 'front' | 'back'
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

export default function CombatFormationRow({
  units,
  isOpponent = false,
  label,
  rowName,
  regenMap,
  activeAttackerId,
  activeTargetId,
  currentTime,
  presentationTracks = [],
  synergies = {},
  traits = [],
  replayEvents = [],
  replayPaused = false,
  reducedMotion = false,
}: Props) {
  return (
    <div className="combat-unit-line">
      <div className="combat-unit-line-label">{label}</div>
      <div className="combat-unit-grid" data-formation-row={rowName}>
        {getFormationSlots(units).map((unit, slotIndex) => unit ? (
          <motion.div
            key={unit.id}
            className="combat-unit-grid-slot"
            data-formation-slot={slotIndex}
            layout="position"
            transition={{ layout: { duration: 0.28, ease: 'easeOut' } }}
          >
            <CombatUnitCard
              unit={unit}
              isOpponent={isOpponent}
              regen={regenMap[unit.id]}
              isActiveAttacker={unit.id === activeAttackerId}
              isActiveTarget={unit.id === activeTargetId}
              currentTime={currentTime}
              presentationTracks={presentationTracks}
              synergies={synergies}
              traits={traits}
              replayEvents={replayEvents}
              replayPaused={replayPaused}
              reducedMotion={reducedMotion}
            />
          </motion.div>
        ) : (
          <div
            key={`empty-${rowName}-${slotIndex}`}
            className="combat-unit-grid-slot combat-unit-grid-slot-placeholder"
            data-formation-slot={slotIndex}
            aria-hidden="true"
          />
        ))}
      </div>
    </div>
  )
}
