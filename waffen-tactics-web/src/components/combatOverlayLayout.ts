export const combatOverlayPanelStyle = {
  backgroundColor: '#1e293b',
  borderRadius: '0.75rem',
  width: 'min(1400px, calc(100vw - 16px))',
  height: 'min(850px, calc(100vh - 16px))',
  maxWidth: 'calc(100vw - 16px)',
  maxHeight: 'calc(100vh - 16px)',
  boxSizing: 'border-box',
  display: 'flex',
  flexDirection: 'row',
  border: '3px solid #475569',
  boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
  overflow: 'hidden',
  position: 'relative',
} as const

export const combatOverlaySidebarStyle = {
  width: 320,
  minWidth: 0,
  minHeight: 0,
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'space-between',
  padding: '1.5rem 1rem',
  borderRight: '2px solid #334155',
  background: 'rgba(30,41,59,0.98)',
  overflowY: 'auto',
  boxSizing: 'border-box',
} as const

export const combatOverlayBoardStyle = {
  flex: 1,
  minWidth: 0,
  minHeight: 0,
  display: 'flex',
  flexDirection: 'column',
  padding: '1.5rem',
  position: 'relative',
  overflow: 'hidden',
} as const

/** Keep the full combat panel available on desktop while giving narrow views
 * the board-first layout they need on first render. */
export function shouldStartCombatPanelCollapsed(viewportWidth: number): boolean {
  return viewportWidth < 900
}
