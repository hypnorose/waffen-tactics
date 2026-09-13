import { createPortal } from 'react-dom'
import { type ReactNode, type RefObject } from 'react'
import { useViewportTooltipPosition } from '../ui/useViewportTooltipPosition'

interface Props {
  anchorRef: RefObject<HTMLElement | null>
  open: boolean
  children: ReactNode
}

const PREVIEW_SIZE = { width: 288, height: 360 }

export default function ItemPreviewTooltip({ anchorRef, open, children }: Props) {
  const { position } = useViewportTooltipPosition({
    open,
    anchorRef,
    size: PREVIEW_SIZE,
  })

  if (!open || !position || typeof document === 'undefined') return null

  return createPortal(
    <div
      data-item-preview
      data-preview-placement={position.placement}
      className="pointer-events-none rounded-lg border border-cyan-300/70 bg-slate-950 px-3 py-2 text-left text-xs shadow-2xl"
      style={{
        position: 'fixed',
        left: position.left,
        top: position.top,
        width: PREVIEW_SIZE.width,
        maxWidth: 'calc(100vw - 16px)',
        maxHeight: 'min(360px, calc(100vh - 16px))',
        boxSizing: 'border-box',
        overflowY: 'auto',
        zIndex: 2100,
      }}
    >
      {children}
    </div>,
    document.body,
  )
}
