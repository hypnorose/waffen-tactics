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
      {combatLog.map((msg, idx) => (
        <div
          key={idx}
          style={{
            marginBottom: 0,
            padding: '2.5px 8px',
            borderRadius: 4,
            background: lineColors[idx % lineColors.length],
            transition: 'background 0.2s',
            whiteSpace: 'pre-wrap',
            fontWeight: 500
          }}
        >
          {msg}
        </div>
      ))}
      <div ref={logEndRef} />
    </div>
  )
}
