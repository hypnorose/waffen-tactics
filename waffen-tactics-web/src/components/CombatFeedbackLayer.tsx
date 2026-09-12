import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useUnitAnchors } from '../hooks/useUnitAnchors'
import { getCombatFeedback } from '../hooks/combat/combatFeedback'
import type { CombatEvent } from '../hooks/combat/types'

interface Point {
  x: number
  y: number
}

interface Props {
  event?: CombatEvent
  eventIndex: number
  replayPaused?: boolean
  reducedMotion?: boolean
}

function samePositions(previous: Record<string, Point>, next: Record<string, Point>): boolean {
  const previousKeys = Object.keys(previous)
  const nextKeys = Object.keys(next)
  if (previousKeys.length !== nextKeys.length) return false
  return nextKeys.every((key) => previous[key]?.x === next[key]?.x && previous[key]?.y === next[key]?.y)
}

export default function CombatFeedbackLayer({ event, eventIndex, replayPaused = false, reducedMotion = false }: Props) {
  const { getCenter } = useUnitAnchors()
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [layoutVersion, setLayoutVersion] = useState(0)
  const [positions, setPositions] = useState<Record<string, Point>>({})
  const feedback = replayPaused ? [] : getCombatFeedback(event)
  const targetKey = feedback.map((entry) => entry.targetId).join('|')

  useEffect(() => {
    const onResize = () => setLayoutVersion((version) => version + 1)
    window.addEventListener('resize', onResize)
    window.visualViewport?.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      window.visualViewport?.removeEventListener('resize', onResize)
    }
  }, [])

  useLayoutEffect(() => {
    if (feedback.length === 0 || !containerRef.current) {
      setPositions((previous) => Object.keys(previous).length === 0 ? previous : {})
      return
    }

    const next: Record<string, Point> = {}
    feedback.forEach((entry) => {
      if (next[entry.targetId]) return
      const center = getCenter(entry.targetId, containerRef.current)
      if (center) next[entry.targetId] = center
    })
    setPositions((previous) => samePositions(previous, next) ? previous : next)
  }, [feedback, getCenter, layoutVersion, targetKey, eventIndex])

  if (feedback.length === 0) return null

  return (
    <div
      ref={containerRef}
      className="combat-feedback-layer"
      data-layout-version={layoutVersion}
      aria-hidden="true"
    >
      <AnimatePresence initial={false}>
        {feedback.map((entry, index) => {
          const center = positions[entry.targetId]
          if (!center) return null
          const verticalOffset = index * 24
          return (
            <div
              key={`${entry.id}:${eventIndex}`}
              className="combat-feedback-anchor"
              style={{ left: center.x, top: center.y - verticalOffset }}
            >
              <div className={`combat-feedback-item combat-feedback-item-${entry.tone}`}>
                <motion.span
                  className="combat-feedback-item-motion"
                  initial={{ opacity: 0, y: reducedMotion ? 0 : 8, scale: reducedMotion ? 1 : 0.92 }}
                  animate={{ opacity: 1, y: reducedMotion ? 0 : -42, scale: 1 }}
                  exit={{ opacity: 0, y: reducedMotion ? 0 : -54 }}
                  transition={{ duration: reducedMotion ? 0.15 : 0.7, ease: 'easeOut' }}
                >
                  {entry.text}
                </motion.span>
              </div>
            </div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
