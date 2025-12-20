import React, { useRef, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useProjectileSystem } from '../hooks/useProjectileSystem'
import { useUnitAnchors } from '../hooks/useUnitAnchors'

export default function ProjectileLayer() {
  const { projectiles } = useProjectileSystem()
  const { getCenter } = useUnitAnchors()
  const containerRef = useRef<HTMLDivElement | null>(null)

  // force reflow on window resize so positions stay correct
  useEffect(() => {
    const onResize = () => {}
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  return (
    <div ref={containerRef} style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 80 }}>
      <AnimatePresence>
        {projectiles.map(p => {
          const start = getCenter(p.fromId, containerRef.current) || { x: 0, y: 0 }
          const end = getCenter(p.toId, containerRef.current) || { x: 0, y: 0 }
          // small random offset/rotation
          const offX = (Math.random() - 0.5) * 12
          const offY = (Math.random() - 0.5) * 12
          const rot = (Math.random() - 0.5) * 20
          const midX = (start.x + end.x) / 2 + (Math.random() - 0.5) * 20
          const midY = (start.y + end.y) / 2 - 40 // vertical arc

          return (
            <motion.div
              key={p.id}
              initial={{ x: start.x + offX, y: start.y + offY, rotate: rot, opacity: 0 }}
              animate={{ 
                x: end.x + offX, 
                y: end.y + offY, 
                rotate: rot + 360, // Full spin during flight
                opacity: 1 
              }}
              exit={{ opacity: 0 }}
              transition={{ 
                duration: Math.max(0.3, Math.min(0.45, p.duration / 1000)), 
                ease: 'easeOut',
                rotate: { duration: Math.max(0.3, Math.min(0.45, p.duration / 1000)), ease: 'linear' } // Linear rotation for smooth spinning
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
