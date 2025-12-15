import React, { RefObject } from 'react'

interface Props {
  combatLog: string[]
  showLog: boolean
  setShowLog: (v: boolean) => void
  logEndRef: RefObject<HTMLDivElement>
}

export default function CombatLog({ combatLog, logEndRef }: Omit<Props, 'showLog' | 'setShowLog'>) {
  const lineColors = ['rgba(51,65,85,0.18)', 'rgba(30,41,59,0.18)'];
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        padding: '0.5rem 0.7rem',
        background: 'transparent',
        overflowY: 'auto',
        fontFamily: 'monospace',
        fontSize: 13,
        color: '#e2e8f0',
        display: 'flex',
        flexDirection: 'column',
        gap: 0
      }}
    >
      {combatLog.map((msg, idx) => {
        // Detect damage messages like: "⚔️ Attacker atakuje Target (12.34 dmg)"
        const dmgMatch = msg.match(/\(([-+0-9.]+)\s*dmg\)/i)
        const isDamage = !!dmgMatch && msg.trim().startsWith('⚔️')
        const amount = isDamage ? dmgMatch![1] : null
        const textWithoutDmg = isDamage ? msg.replace(/\s*\([^)]+dmg\)/i, '') : msg
        return (
          <div
            key={idx}
            style={{
              marginBottom: 0,
              padding: '2.5px 8px',
              borderRadius: 4,
              background: lineColors[idx % lineColors.length],
              transition: 'background 0.2s',
              whiteSpace: 'pre-wrap',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: 8
            }}
          >
            {isDamage ? (
              <>
                <span style={{ marginRight: 6 }}>{textWithoutDmg.split(' ')[0]}</span>
                <span style={{ background: 'rgba(220,38,38,0.95)', color: 'white', padding: '2px 6px', borderRadius: 6, fontWeight: 800 }}>{amount}</span>
                <span style={{ opacity: 0.9 }}>{' ' + textWithoutDmg.split(' ').slice(1).join(' ')}</span>
              </>
            ) : (
              <span>{msg}</span>
            )}
          </div>
        )
      })}
      <div ref={logEndRef} />
    </div>
  )
}
