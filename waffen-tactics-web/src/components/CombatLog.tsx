import { RefObject } from 'react'

interface Props {
  combatLog: string[]
  showLog: boolean
  setShowLog: (v: boolean) => void
  logEndRef: RefObject<HTMLDivElement>
}

function parseLogLine(msg: string) {
  const match = msg.match(/^\[([A-Z]+)\]\s*(.*)$/)
  const tag = match?.[1] || null
  const body = match?.[2] || msg
  return { tag, body }
}

function tagStyle(tag: string | null) {
  switch (tag) {
    case 'ATK':
      return { background: 'rgba(239, 68, 68, 0.16)', color: '#fecaca', border: '1px solid rgba(239, 68, 68, 0.35)' }
    case 'BONUS':
      return { background: 'rgba(249, 115, 22, 0.18)', color: '#fdba74', border: '1px solid rgba(249, 115, 22, 0.35)' }
    case 'DEATH':
      return { background: 'rgba(71, 85, 105, 0.18)', color: '#cbd5e1', border: '1px solid rgba(71, 85, 105, 0.3)' }
    case 'BUFF':
    case 'DEBUFF':
    case 'SHIELD':
    case 'STUN':
      return { background: 'rgba(59, 130, 246, 0.14)', color: '#bfdbfe', border: '1px solid rgba(59, 130, 246, 0.3)' }
    case 'HEAL':
    case 'REGEN':
      return { background: 'rgba(16, 185, 129, 0.14)', color: '#bbf7d0', border: '1px solid rgba(16, 185, 129, 0.3)' }
    case 'MANA':
      return { background: 'rgba(139, 92, 246, 0.14)', color: '#ddd6fe', border: '1px solid rgba(139, 92, 246, 0.3)' }
    case 'RESULT':
      return { background: 'rgba(250, 204, 21, 0.12)', color: '#fde68a', border: '1px solid rgba(250, 204, 21, 0.28)' }
    case 'DOT':
      return { background: 'rgba(244, 114, 182, 0.12)', color: '#fbcfe8', border: '1px solid rgba(244, 114, 182, 0.28)' }
    default:
      return { background: 'rgba(51, 65, 85, 0.18)', color: '#e2e8f0', border: '1px solid transparent' }
  }
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
        const parsed = parseLogLine(msg)
        const fallbackEffect =
          !parsed.tag && (
            msg.includes('tarcz') || msg.includes('shield') ? 'SHIELD'
              : msg.includes('regeneruje') || msg.includes('heals') ? 'HEAL'
              : msg.includes('ogłusz') || msg.includes('stun') ? 'STUN'
              : msg.includes('DoT') || msg.includes('obrażeń w czasie') ? 'DOT'
              : (msg.includes('zyskuje') || msg.includes('traci') || msg.includes('buff') || msg.includes('debuff')) ? 'BUFF'
              : null
          )
        const effectTag = parsed.tag || fallbackEffect
        const styles = tagStyle(effectTag)

        return (
          <div
            key={idx}
            style={{
              marginBottom: 0,
              padding: '3px 8px',
              borderRadius: 4,
              background: effectTag ? styles.background : lineColors[idx % lineColors.length],
              border: effectTag ? styles.border : '1px solid transparent',
              transition: 'background 0.2s',
              whiteSpace: 'pre-wrap',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              minHeight: 24,
            }}
          >
            {effectTag ? (
              <>
                <span style={{ background: styles.color, color: '#0f172a', padding: '2px 6px', borderRadius: 6, fontWeight: 800, fontSize: 11 }}>
                  {effectTag}
                </span>
                <span>{parsed.body}</span>
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
