import { createPortal } from 'react-dom'
import { useCallback, useEffect, useState, type ReactNode, type RefObject } from 'react'
import { getItemTooltipPosition, type ItemTooltipPosition } from './itemTooltipPosition'

interface Props {
  anchorRef: RefObject<HTMLElement | null>
  open: boolean
  children: ReactNode
}

const PREVIEW_SIZE = { width: 288, height: 360 }

export default function ItemPreviewTooltip({ anchorRef, open, children }: Props) {
  const [position, setPosition] = useState<ItemTooltipPosition | null>(null)

  const updatePosition = useCallback(() => {
    const anchor = anchorRef.current
    if (!anchor) return
    setPosition(getItemTooltipPosition(anchor.getBoundingClientRect(), {
      width: window.innerWidth,
      height: window.innerHeight,
    }, PREVIEW_SIZE))
  }, [anchorRef])

  useEffect(() => {
    if (!open) {
      setPosition(null)
      return
    }
    updatePosition()
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)
    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [open, updatePosition])

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
