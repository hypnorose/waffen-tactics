import { memo } from 'react'
import { motion } from 'framer-motion'
import CombatUnitCard from './CombatUnitCard'

interface Props {
  units: any[]
  attackingUnits: string[]
  targetUnits: string[]
  regenMap: Record<string, any>
}

const PlayerUnits = memo(function PlayerUnits({ units, attackingUnits, targetUnits, regenMap }: Props) {
  return (
    <div className="bg-gray-800 rounded-lg p-3 border border-gray-700" style={{ flexShrink: 0 }}>
      <h3 className="text-sm font-bold text-green-400 mb-2 text-center">🛡️ Twoje Jednostki</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.5rem', maxHeight: '300px', overflowY: 'auto' }}>
        {units.map((u: any) => (
          <motion.div
            key={u.id}
          >
            <CombatUnitCard
              unit={u}
              attackingUnits={attackingUnits}
              targetUnits={targetUnits}
              regen={regenMap[u.id]}
            />
          </motion.div>
        ))}
      </div>
    </div>
  )
})

export default PlayerUnits
