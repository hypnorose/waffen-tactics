import { memo } from 'react'
import { motion } from 'framer-motion'
import CombatUnitCard from './CombatUnitCard'

interface Props {
  units: any[]
  attackingUnits: string[]
  targetUnits: string[]
  skillUnits: string[]
  regenMap: Record<string, any>
  attackDurations?: Record<string, number>
}

const OpponentUnits = memo(function OpponentUnits({ units, attackingUnits, targetUnits, skillUnits, regenMap, attackDurations = {} }: Props) {
  const frontUnits = units.filter(u => u.position === 'front')
  const backUnits = units.filter(u => u.position === 'back')

  return (
    <div className="bg-gray-800 rounded-lg p-3 border border-gray-700" style={{ flexShrink: 0, width: '100%' }}>
      <h3 className="text-sm font-bold text-red-400 mb-2 text-center">⚔️ Przeciwnik</h3>
      
      {/* Back Line (now displayed first) */}
      {backUnits.length > 0 && (
        <div className="mb-3">
          <div className="text-xs text-gray-400 mb-1">Linia Tylna</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.5rem', maxHeight: '200px', overflow: 'visible' }}>
            {backUnits.map((u: any) => (
              <motion.div
                key={u.id}
              >
                <CombatUnitCard
                  unit={u}
                  isOpponent
                  attackingUnits={attackingUnits}
                  targetUnits={targetUnits}
                  skillUnits={skillUnits}
                  regen={regenMap[u.id]}
                  attackDuration={attackDurations[u.id]}
                />
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Front Line (now displayed second) */}
      {frontUnits.length > 0 && (
        <div>
          <div className="text-xs text-gray-400 mb-1">Linia Frontowa</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.5rem', maxHeight: '200px', overflow: 'visible' }}>
            {frontUnits.map((u: any) => (
              <motion.div
                key={u.id}
              >
                <CombatUnitCard
                  unit={u}
                  isOpponent
                  attackingUnits={attackingUnits}
                  targetUnits={targetUnits}
                  skillUnits={skillUnits}
                  regen={regenMap[u.id]}
                  attackDuration={attackDurations[u.id]}
                />
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
})

export default OpponentUnits
