import { createPortal } from 'react-dom'
import { useCallback, useEffect, useState } from 'react'
import type { Item } from '../data/items'
import { ItemRecipePreviewContent } from './ItemPreviewContent'
import { getItemTooltipPosition, type ItemTooltipPosition } from './itemTooltipPosition'

interface Props {
  first: Item
  second: Item
  result?: Item
  itemCatalog: Item[]
  anchor: HTMLElement
}

const PREVIEW_SIZE = { width: 320, height: 360 }

export default function ItemRecipePreviewTooltip({ first, second, result, itemCatalog, anchor }: Props) {
  const [position, setPosition] = useState<ItemTooltipPosition | null>(null)

  const updatePosition = useCallback(() => {
    if (typeof window === 'undefined') return
    setPosition(getItemTooltipPosition(anchor.getBoundingClientRect(), {
      width: window.innerWidth,
      height: window.innerHeight,
    }, PREVIEW_SIZE))
  }, [anchor])

  useEffect(() => {
    updatePosition()
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)
    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [updatePosition])

  if (!position || typeof document === 'undefined') return null

  return createPortal(
    <div
      data-item-preview
      data-item-recipe-preview
      data-tooltip-placement={position.placement}
      role="tooltip"
      className="pointer-events-none rounded-lg border border-cyan-300/60 bg-slate-950 px-3 py-2 text-left text-xs shadow-2xl"
      style={{
        position: 'fixed',
        left: position.left,
        top: position.top,
        width: 'max-content',
        maxWidth: 'min(320px, calc(100vw - 16px))',
        maxHeight: 'min(360px, calc(100vh - 16px))',
        boxSizing: 'border-box',
        overflowY: 'auto',
        overflowWrap: 'anywhere',
        zIndex: 2001,
      }}
    >
      <ItemRecipePreviewContent first={first} second={second} result={result} itemCatalog={itemCatalog} />
    </div>,
    document.body,
  )
}
