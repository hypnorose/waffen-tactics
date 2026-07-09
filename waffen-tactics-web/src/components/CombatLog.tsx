import { RefObject } from 'react'

interface Props {
  combatLog: string[]
  showLog: boolean
  setShowLog: (v: boolean) => void
  logEndRef: RefObject<HTMLDivElement>
}

export default function CombatLog({ combatLog, logEndRef }: Omit<Props, 'showLog' | 'setShowLog'>) {
  const lineColors = ['rgba(51,65,85,0.18)', 'rgba(30,41,59,0.18)']

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
        gap: 0,
      }}
    >
      {combatLog.map((msg, idx) => {
        const dmgMatch = msg.match(/\(([-+0-9.]+)\s*dmg\)/i)
        const isDamage = !!dmgMatch && (msg.includes('ATTACK:') || msg.trim().startsWith('⚔'))
        const effectLabel =
          msg.match(/^(BUFF|DEBUFF|STUN|DOT|SHIELD|HEAL):\s*/)?.[1] ||
          (msg.includes('tarcz') || msg.includes('shield') ? 'SHIELD'
            : msg.includes('regeneruje') || msg.includes('heals') ? 'HEAL'
            : msg.includes('ogłusz') || msg.includes('stun') ? 'STUN'
            : msg.includes('DoT') || msg.includes('obrażeń w czasie') ? 'DOT'
            : (msg.includes('zyskuje') || msg.includes('traci') || msg.includes('buff') || msg.includes('debuff')) ? 'BUFF'
            : null)
        const isEffect = !!effectLabel
        const amount = isDamage ? dmgMatch![1] : null
        const textWithoutDmg = isDamage ? msg.replace(/\s*\([^)]+dmg\)/i, '') : msg

        return (
          <div
            key={idx}
            style={{
              marginBottom: 0,
              padding: '2.5px 8px',
              borderRadius: 4,
              background: isEffect ? 'rgba(59,130,246,0.12)' : lineColors[idx % lineColors.length],
              border: isEffect ? '1px solid rgba(59,130,246,0.3)' : '1px solid transparent',
              transition: 'background 0.2s',
              whiteSpace: 'pre-wrap',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            {isDamage ? (
              <>
                <span style={{ marginRight: 6 }}>{textWithoutDmg.split(' ')[0]}</span>
                <span style={{ background: 'rgba(220,38,38,0.95)', color: 'white', padding: '2px 6px', borderRadius: 6, fontWeight: 800 }}>{amount}</span>
                <span style={{ opacity: 0.9 }}>{' ' + textWithoutDmg.split(' ').slice(1).join(' ')}</span>
              </>
            ) : isEffect ? (
              <>
                <span style={{ background: 'rgba(59,130,246,0.95)', color: 'white', padding: '2px 6px', borderRadius: 6, fontWeight: 800 }}>{effectLabel}</span>
                <span>{msg.replace(/^[A-Z]+:\s*/, '')}</span>
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
