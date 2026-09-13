import React from 'react'

interface Props {
  opponentInfo: { name: string; wins: number; level: number; avatar?: string } | null
  combatSpeed: number
  setCombatSpeed: (v: number) => void
}

function CombatHeader({ opponentInfo }: Omit<Props, 'combatSpeed' | 'setCombatSpeed'>) {
  return (
    <section className="combat-header">
      <div className="combat-header-kicker">MATCHUP</div>
      <div className="combat-header-main">
        <div className="combat-header-opponent">
          {opponentInfo ? (
            <>
              {opponentInfo.avatar ? (
                <img src={opponentInfo.avatar} alt={opponentInfo.name} className="combat-header-avatar" />
              ) : (
                <div className="combat-header-avatar combat-header-avatar-placeholder" aria-hidden="true" />
              )}
              <div className="combat-header-copy">
                <div className="combat-header-label">Przeciwnik</div>
                <div className="combat-header-name">{opponentInfo.name}</div>
                <div className="combat-header-meta">
                  Poziom <strong>{opponentInfo.level}</strong>
                  <span aria-hidden="true">/</span>
                  Wygrane <strong>{opponentInfo.wins}</strong>
                </div>
              </div>
            </>
          ) : (
            <div className="combat-header-empty">Brak danych o przeciwniku</div>
          )}
        </div>
      </div>
    </section>
  )
}

export default CombatHeader
