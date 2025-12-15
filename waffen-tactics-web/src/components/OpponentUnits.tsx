import CombatUnitCard from './CombatUnitCard'

interface Props {
  units: any[]
  attackingUnit: string | null
  targetUnit: string | null
  regenMap: Record<string, any>
}

export default function OpponentUnits({ units, attackingUnit, targetUnit, regenMap }: Props) {
  return (
    <div className="bg-gray-800 rounded-lg p-3 border border-gray-700" style={{ flexShrink: 0 }}>
      <h3 className="text-sm font-bold text-red-400 mb-2 text-center">⚔️ Przeciwnik</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.5rem', maxHeight: '400px', overflowY: 'auto' }}>
        {units.map((u: any) => (
          <CombatUnitCard
            key={u.id}
            unit={u}
            isOpponent
            attackingUnit={attackingUnit}
            targetUnit={targetUnit}
            regen={regenMap[u.id]}
          />
        ))}
      </div>
    </div>
  )
}
