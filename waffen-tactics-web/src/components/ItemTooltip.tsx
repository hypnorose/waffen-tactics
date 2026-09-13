import { createPortal } from 'react-dom'
import { useCallback, useEffect, useRef, useState, type HTMLAttributes, type ReactNode } from 'react'
import type { Item } from '../data/items'
import ItemTooltipContent from './ItemTooltipContent'
import { useViewportTooltipPosition } from '../ui/useViewportTooltipPosition'

interface Props {
  item: Item
  itemCatalog: Item[]
  children: ReactNode
  className?: string
  triggerProps?: HTMLAttributes<HTMLDivElement> & { [key: `data-${string}`]: string | undefined }
}

const CLOSE_DELAY_MS = 120

export default function ItemTooltip({ item, itemCatalog, children, className, triggerProps }: Props) {
  const [isOpen, setIsOpen] = useState(false)
  const triggerRef = useRef<HTMLDivElement | null>(null)
  const tooltipRef = useRef<HTMLDivElement | null>(null)
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { position } = useViewportTooltipPosition({
    open: isOpen,
    anchorRef: triggerRef,
    measuredRef: tooltipRef,
    size: { width: 256, height: 360 },
  })

  const cancelClose = useCallback(() => {
    if (closeTimer.current) clearTimeout(closeTimer.current)
    closeTimer.current = null
  }, [])

  const scheduleClose = useCallback(() => {
    cancelClose()
    closeTimer.current = setTimeout(() => setIsOpen(false), CLOSE_DELAY_MS)
  }, [cancelClose])

  useEffect(() => () => {
    cancelClose()
  }, [cancelClose])

  const {
    onMouseEnter: onTriggerMouseEnter,
    onMouseLeave: onTriggerMouseLeave,
    onFocus: onTriggerFocus,
    onBlur: onTriggerBlur,
    onClick: onTriggerClick,
    ...restTriggerProps
  } = triggerProps || {}

  return (
    <div
      {...restTriggerProps}
      ref={triggerRef}
      className={className}
      role="button"
      aria-expanded={isOpen}
      onMouseEnter={event => {
        onTriggerMouseEnter?.(event)
        cancelClose()
        setIsOpen(true)
      }}
      onMouseLeave={event => {
        onTriggerMouseLeave?.(event)
        scheduleClose()
      }}
      onFocus={event => {
        onTriggerFocus?.(event)
        cancelClose()
        setIsOpen(true)
      }}
      onBlur={event => {
        onTriggerBlur?.(event)
        scheduleClose()
      }}
      onClick={event => {
        onTriggerClick?.(event)
        if (event.defaultPrevented) return
        cancelClose()
        setIsOpen(open => !open)
      }}
    >
      {children}
      {isOpen && position && typeof document !== 'undefined' && createPortal(
        <div
          data-item-tooltip
          data-tooltip-placement={position.placement}
          ref={tooltipRef}
          role="tooltip"
          className="pointer-events-auto rounded-lg border border-amber-300/60 bg-slate-950 px-3 py-2 text-left text-xs shadow-2xl"
          style={{
            position: 'fixed',
            left: position.left,
            top: position.top,
            width: 256,
            maxWidth: 'calc(100vw - 16px)',
            maxHeight: 'min(360px, calc(100vh - 16px))',
            boxSizing: 'border-box',
            overflowY: 'auto',
            zIndex: 2000,
          }}
          onMouseEnter={cancelClose}
          onMouseLeave={scheduleClose}
        >
          <ItemTooltipContent item={item} itemCatalog={itemCatalog} />
        </div>,
        document.body,
      )}
    </div>
  )
}
