import React from 'react'

interface Props {
  opponentInfo: { name: string; wins: number; level: number; avatar?: string } | null
  combatSpeed: number
  setCombatSpeed: (v: number) => void
}

function CombatHeader({ opponentInfo }: Omit<Props, 'combatSpeed' | 'setCombatSpeed'>) {
  return (
    <div style={{ background: '#23293a', borderRadius: 12, border: '2px solid #334155', padding: '18px 18px 10px 18px', marginBottom: 12, boxShadow: '0 2px 12px rgba(0,0,0,0.18)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 18 }}>
        {/* Info o przeciwniku */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-start', gap: 12 }}>
          {opponentInfo ? (
            <>
              {/* Avatar */}
              {opponentInfo.avatar ? (
                <img src={opponentInfo.avatar} alt={opponentInfo.name} style={{ width: 72, height: 72, borderRadius: 8, objectFit: 'cover', border: '2px solid #334155' }} />
              ) : (
                <div style={{ width: 72, height: 72, borderRadius: 8, background: '#0f1724', border: '2px solid #334155' }} />
              )}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', justifyContent: 'center' }}>
                <div style={{ color: '#fbbf24', fontWeight: 700, fontSize: 18, letterSpacing: 0.5, marginBottom: 2 }}>Przeciwnik</div>
                <div style={{ color: '#e2e8f0', fontWeight: 600, fontSize: 16 }}>{opponentInfo.name}</div>
                <div style={{ color: '#94a3b8', fontSize: 13 }}>Poziom: <span style={{ color: '#fbbf24', fontWeight: 700 }}>{opponentInfo.level}</span> | Wygrane: <span style={{ color: '#f87171', fontWeight: 700 }}>{opponentInfo.wins}</span></div>
              </div>
            </>
          ) : (
            <div style={{ color: '#64748b', fontSize: 15 }}>Brak danych o przeciwniku</div>
          )}
        </div>

        {/* Tytuł */}
        
      </div>
    </div>
  )
}

export default CombatHeader
