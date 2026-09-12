import React, { useRef, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useProjectileSystem, type Projectile } from '../hooks/useProjectileSystem'
import { useUnitAnchors } from '../hooks/useUnitAnchors'
import type { PresentationDiagnostic } from '../hooks/combat/animation/presentationTimeline'

export type ProjectileEndpoint = { x: number; y: number }

export function resolveProjectileEndpoints(
  getCenter: (id: string, relativeTo?: Element | null) => ProjectileEndpoint | null,
  projectile: Pick<Projectile, 'fromId' | 'toId'>,
  relativeTo: Element | null,
): { start: ProjectileEndpoint; end: ProjectileEndpoint } | null {
  const start = getCenter(projectile.fromId, relativeTo)
  const end = getCenter(projectile.toId, relativeTo)
  if (!start || !end) return null
  return { start, end }
}

interface Props {
  onDiagnostic?: (diagnostic: PresentationDiagnostic) => void
}

function stableUnit(id: string, salt: number): number {
  let hash = 2166136261 ^ salt
  for (let index = 0; index < id.length; index += 1) {
    hash = Math.imul(hash ^ id.charCodeAt(index), 16777619)
  }
  return ((hash >>> 0) % 1000) / 1000
}

export default function ProjectileLayer({ onDiagnostic }: Props) {
  const { projectiles } = useProjectileSystem()
  const { getCenter } = useUnitAnchors()
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [layoutVersion, setLayoutVersion] = useState(0)

  // Re-render on resize so an in-flight projectile follows the current anchors.
  useEffect(() => {
    const onResize = () => setLayoutVersion((version) => version + 1)
    window.addEventListener('resize', onResize)
    window.visualViewport?.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      window.visualViewport?.removeEventListener('resize', onResize)
    }
  }, [])

  useEffect(() => {
    if (!onDiagnostic || projectiles.length === 0) return
    const timer = window.setTimeout(() => {
      projectiles.forEach((projectile) => {
        const missingId = !getCenter(projectile.fromId) ? projectile.fromId : !getCenter(projectile.toId) ? projectile.toId : null
        if (!missingId) return
        onDiagnostic({
          code: 'missing_actor',
          message: `Projectile ${projectile.id} has no registered visual anchor for ${missingId}.`,
          eventType: 'projectile',
          eventId: projectile.sourceEventId,
          seq: projectile.sourceSeq,
          unitId: missingId,
        })
      })
    }, 0)
    return () => window.clearTimeout(timer)
  }, [getCenter, onDiagnostic, projectiles])

  return (
    <div ref={containerRef} data-layout-version={layoutVersion} style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 80 }}>
      <AnimatePresence>
        {projectiles.map(p => {
          // Never render a projectile from guessed coordinates. The diagnostic
          // effect above reports the missing actor/target separately.
          const endpoints = resolveProjectileEndpoints(getCenter, p, containerRef.current)
          if (!endpoints) return null
          const { start, end } = endpoints
          // Stable per-projectile offsets keep replay visuals reproducible.
          const offX = (stableUnit(p.id, 1) - 0.5) * 12
          const offY = (stableUnit(p.id, 2) - 0.5) * 12
          const rot = (stableUnit(p.id, 3) - 0.5) * 20
          const midX = (start.x + end.x) / 2 + (stableUnit(p.id, 4) - 0.5) * 20
          const midY = (start.y + end.y) / 2 - 40 // vertical arc
          const duration = Math.max(0.3, Math.min(0.45, p.duration / 1000))

          return (
            <motion.div
              key={p.id}
              initial={{ x: start.x + offX, y: start.y + offY, rotate: rot, opacity: 0 }}
              animate={{ 
                x: [start.x + offX, midX + offX, end.x + offX],
                y: [start.y + offY, midY + offY, end.y + offY],
                rotate: [rot, rot + 180, rot + 360],
                opacity: 1 
              }}
              exit={{ opacity: 0 }}
              transition={{ 
                duration,
                ease: 'easeOut',
                times: [0, 0.55, 1],
                rotate: { duration, ease: 'linear' }
              }}
              style={{ position: 'absolute', left: 0, top: 0, transformOrigin: 'center center', fontSize: 24 }}
            >
              <div style={{ display: 'inline-block' }}>{p.emoji}</div>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
