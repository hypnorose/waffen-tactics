import React from 'react'
import type { DesyncEntry } from '../hooks/combat/types'

interface Props {
  desyncLogs: DesyncEntry[]
  onClear: () => void
  onExport: () => string
}

export default function DesyncInspector({ desyncLogs, onClear, onExport }: Props) {
  const download = () => {
    const json = onExport()
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `desync_logs_${Date.now()}.json`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  return (
    <div
      id="desync-inspector"
      role="dialog"
      aria-label="Desync log"
      style={{ position: 'fixed', right: 16, bottom: 16, width: 'min(520px, calc(100vw - 32px))', maxHeight: 'min(60vh, 520px)', overflow: 'auto', background: '#0f172a', color: '#e2e8f0', border: '1px solid #334155', borderRadius: 8, padding: 12, zIndex: 200, boxSizing: 'border-box' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <strong>Desync log ({desyncLogs.length})</strong>
        <div>
          <button type="button" onClick={download} style={{ marginRight: 8, background: '#2563eb', color: 'white', border: 'none', padding: '6px 10px', borderRadius: 6 }}>Export</button>
          <button type="button" onClick={onClear} style={{ background: '#334155', color: '#f1f5f9', border: 'none', padding: '6px 10px', borderRadius: 6 }}>Clear</button>
        </div>
      </div>
      <div style={{ fontSize: 12 }}>
        {desyncLogs.length === 0 && <div style={{ opacity: 0.7 }}>No desyncs recorded.</div>}
        {desyncLogs.map((d, idx) => (
          <div key={`${d.unit_id}_${idx}`} style={{ padding: 8, background: '#071029', borderRadius: 6, marginBottom: 8, border: '1px solid #0b1220' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontWeight: 700 }}>{d.unit_name || d.unit_id}</div>
                <div style={{ fontSize: 11, opacity: 0.8 }}>
                  {d.note || ''} {d.seq !== undefined && d.seq !== null ? `seq:${d.seq}` : ''} {d.event_id ? `event:${d.event_id}` : 'event:unknown'} {d.timestamp !== undefined && d.timestamp !== null ? `@${new Date(d.timestamp).toLocaleTimeString()}` : ''}
                </div>
              </div>
              <div style={{ textAlign: 'right', fontSize: 12, opacity: 0.9 }}>{d.pending_events?.length ?? 0} pending</div>
            </div>
            <details style={{ marginTop: 8 }}>
              <summary style={{ cursor: 'pointer' }}>Diff</summary>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 11, marginTop: 6 }}>{JSON.stringify(d.diff, null, 2)}</pre>
            </details>
            <details style={{ marginTop: 8 }}>
              <summary style={{ cursor: 'pointer' }}>Pending Events (sample)</summary>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 11, marginTop: 6 }}>{JSON.stringify(d.pending_events?.slice(0,10) || [], null, 2)}</pre>
            </details>
            <details style={{ marginTop: 8 }}>
              <summary style={{ cursor: 'pointer' }}>Recent Events (last 25)</summary>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 11, marginTop: 6 }}>{JSON.stringify(d.recent_events || [], null, 2)}</pre>
            </details>
          </div>
        ))}
      </div>
    </div>
  )
}
