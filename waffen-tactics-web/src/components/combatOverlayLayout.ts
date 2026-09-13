export const combatOverlayPanelStyle = {
  backgroundColor: '#0b111a',
  borderRadius: '1.25rem',
  width: 'min(1500px, calc(100vw - 32px))',
  height: 'min(900px, calc(100dvh - 32px))',
  maxWidth: 'calc(100vw - 32px)',
  maxHeight: 'calc(100dvh - 32px)',
  boxSizing: 'border-box',
  display: 'flex',
  flexDirection: 'row',
  border: '1px solid rgba(143, 163, 187, 0.22)',
  boxShadow: '0 24px 70px rgba(0, 0, 0, 0.52)',
  overflow: 'hidden',
  position: 'relative',
} as const

export const combatOverlaySidebarStyle = {
  width: 'min(320px, 86vw)',
  minWidth: 'min(320px, 86vw)',
  minHeight: 0,
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'space-between',
  padding: '1rem',
  borderRight: '1px solid rgba(143, 163, 187, 0.2)',
  background: 'rgba(12, 19, 29, 0.98)',
  overflowY: 'auto',
  position: 'absolute',
  inset: '0 auto 0 0',
  zIndex: 140,
  boxSizing: 'border-box',
} as const

export const combatOverlayBoardStyle = {
  flex: 1,
  minWidth: 0,
  minHeight: 0,
  display: 'flex',
  flexDirection: 'column',
  padding: '1.25rem',
  position: 'relative',
  overflow: 'hidden',
} as const

/** The fight is the primary surface; summary/replay tools start as a drawer. */
export function shouldStartCombatPanelCollapsed(viewportWidth: number): boolean {
  void viewportWidth
  return true
}
