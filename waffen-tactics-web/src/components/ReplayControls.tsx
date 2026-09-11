import type { CombatEvent } from '../hooks/combat/types'

interface Props {
  eventCount: number
  currentIndex: number
  currentEvent?: CombatEvent
  isPlaying: boolean
  error?: string | null
  disabled?: boolean
  onRestart: () => void
  onTogglePlay: () => void
  onSeek: (index: number) => void
}

export default function ReplayControls({
  eventCount,
  currentIndex,
  currentEvent,
  isPlaying,
  error,
  disabled = false,
  onRestart,
  onTogglePlay,
  onSeek,
}: Props) {
  const hasEvents = eventCount > 0
  const controlsDisabled = disabled || !hasEvents
  const maxIndex = Math.max(0, eventCount - 1)
  const selectedIndex = hasEvents ? Math.min(Math.max(currentIndex, 0), maxIndex) : 0
  const timeLabel = typeof currentEvent?.timestamp === 'number'
    ? `t=${currentEvent.timestamp.toFixed(2)} s`
    : 'czas nieznany'
  const eventLabel = hasEvents
    ? `${disabled ? 'Replay zatrzymany · ' : ''}Zdarzenie ${selectedIndex + 1} z ${eventCount} · ${timeLabel}`
    : 'Oczekiwanie na canonical replay'

  return (
    <div
      aria-label="Sterowanie replayem walki"
      style={{
        position: 'absolute',
        left: 12,
        right: 12,
        bottom: 12,
        zIndex: 80,
        display: 'grid',
        gridTemplateColumns: 'auto auto minmax(120px, 1fr)',
        alignItems: 'center',
        gap: 8,
        padding: '8px 10px',
        border: '1px solid rgba(148,163,184,0.45)',
        borderRadius: 8,
        background: 'rgba(2,6,23,0.94)',
        color: '#e2e8f0',
        boxShadow: '0 8px 24px rgba(0,0,0,0.35)',
      }}
    >
      <button
        type="button"
        onClick={onRestart}
        disabled={controlsDisabled}
        aria-label="Uruchom replay od początku"
        style={{
          border: '1px solid rgba(251,191,36,0.6)',
          borderRadius: 6,
          padding: '5px 8px',
          background: controlsDisabled ? '#1e293b' : '#334155',
          color: controlsDisabled ? '#64748b' : '#fde68a',
          cursor: controlsDisabled ? 'not-allowed' : 'pointer',
          fontWeight: 700,
        }}
      >
        ↺ Start
      </button>
      <button
        type="button"
        onClick={onTogglePlay}
        disabled={controlsDisabled}
        aria-label={isPlaying ? 'Wstrzymaj replay' : 'Wznów replay'}
        style={{
          border: '1px solid rgba(96,165,250,0.6)',
          borderRadius: 6,
          padding: '5px 8px',
          background: controlsDisabled ? '#1e293b' : '#334155',
          color: controlsDisabled ? '#64748b' : '#bfdbfe',
          cursor: controlsDisabled ? 'not-allowed' : 'pointer',
          fontWeight: 700,
        }}
      >
        {isPlaying ? 'Ⅱ Pauza' : '▶ Odtwarzaj'}
      </button>
      <label style={{ display: 'grid', gap: 2, minWidth: 0 }}>
        <span style={{ fontSize: 11, color: '#cbd5e1', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {eventLabel}
        </span>
        <input
          type="range"
          min="0"
          max={maxIndex}
          step="1"
          value={selectedIndex}
          disabled={controlsDisabled}
          aria-label="Pozycja replayu"
          aria-valuetext={eventLabel}
          onChange={event => onSeek(Number(event.currentTarget.value))}
          style={{ width: '100%', accentColor: '#fbbf24', cursor: controlsDisabled ? 'not-allowed' : 'pointer' }}
        />
      </label>
      {error && (
        <div role="alert" style={{ gridColumn: '1 / -1', color: '#fecaca', fontSize: 11 }}>
          {error}
        </div>
      )}
    </div>
  )
}
