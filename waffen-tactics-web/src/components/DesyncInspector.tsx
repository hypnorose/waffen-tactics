import React from 'react'

interface DesyncEntry {
  unit_id: string
  unit_name?: string
  seq?: number | null
  timestamp?: number | null
  diff: Record<string, { ui: any, server: any }>
  pending_events: any[]
  note?: string
}

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

  if (!import.meta.env.DEV) return null

  return (
    <div style={{ position: 'fixed', right: 20, bottom: 20, width: 520, maxHeight: '60vh', overflow: 'auto', background: '#0f172a', color: '#e2e8f0', border: '1px solid #334155', borderRadius: 8, padding: 12, zIndex: 200 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <strong>Desync Inspector</strong>
        <div>
          <button onClick={download} style={{ marginRight: 8, background: '#2563eb', color: 'white', border: 'none', padding: '6px 10px', borderRadius: 6 }}>Export</button>
          <button onClick={onClear} style={{ background: '#334155', color: '#f1f5f9', border: 'none', padding: '6px 10px', borderRadius: 6 }}>Clear</button>
        </div>
      </div>
      <div style={{ fontSize: 12 }}>
        {desyncLogs.length === 0 && <div style={{ opacity: 0.7 }}>No desyncs recorded.</div>}
        {desyncLogs.map((d, idx) => (
          <div key={`${d.unit_id}_${idx}`} style={{ padding: 8, background: '#071029', borderRadius: 6, marginBottom: 8, border: '1px solid #0b1220' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontWeight: 700 }}>{d.unit_name || d.unit_id}</div>
                <div style={{ fontSize: 11, opacity: 0.8 }}>{d.note || ''} {d.seq ? `seq:${d.seq}` : ''} {d.timestamp ? `@${new Date(d.timestamp).toLocaleTimeString()}` : ''}</div>
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
          </div>
        ))}
      </div>
    </div>
  )
}
