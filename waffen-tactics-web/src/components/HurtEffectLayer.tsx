import { motion, AnimatePresence } from 'framer-motion'
import { useHurtEffects } from '../hooks/useHurtEffects'
import { useUnitAnchors } from '../hooks/useUnitAnchors'

export default function HurtEffectLayer() {
  const { activeEffects } = useHurtEffects()
  const { getCenter } = useUnitAnchors()

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      pointerEvents: 'none',
      zIndex: 1000
    }}>
      <AnimatePresence>
        {activeEffects.map((effect) => {
          const center = getCenter(effect.unitId)
          if (!center) return null

          const { x, y } = center

          if (effect.type === 'flash') {
            return (
              <motion.div
                key={effect.id}
                initial={{ scale: 0, opacity: 1 }}
                animate={{ 
                  scale: [0, 1.5, 2], 
                  opacity: [1, 0.8, 0],
                  rotate: [0, 180, 360]
                }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.18, ease: 'easeOut' }}
                style={{
                  position: 'absolute',
                  left: x - 60,
                  top: y - 60,
                  width: 120,
                  height: 120,
                  background: 'radial-gradient(circle, rgba(255,255,255,1) 0%, rgba(255,150,0,0.9) 30%, rgba(255,0,0,0.7) 60%, transparent 80%)',
                  borderRadius: '50%',
                  pointerEvents: 'none',
                  boxShadow: '0 0 30px rgba(255,100,0,0.8), 0 0 60px rgba(255,50,0,0.4)'
                }}
              />
            )
          }

          if (effect.type === 'shake') {
            return (
              <motion.div
                key={effect.id}
                initial={{ scale: 1, rotate: 0 }}
                animate={{
                  scale: [1, 1.1, 1],
                  rotate: [0, -5, 5, -3, 3, 0],
                  x: [0, -2, 2, -1, 1, 0]
                }}
                exit={{ scale: 1, rotate: 0 }}
                transition={{ duration: 0.4, ease: 'easeOut' }}
                style={{
                  position: 'absolute',
                  left: x - 40,
                  top: y - 40,
                  width: 80,
                  height: 80,
                  background: 'rgba(255, 0, 0, 0.3)',
                  borderRadius: '50%',
                  pointerEvents: 'none'
                }}
              />
            )
          }

          if (effect.type === 'explosion') {
            return (
              <div key={effect.id} style={{ position: 'absolute', left: x - 50, top: y - 50 }}>
                {/* Central flash */}
                <motion.div
                  initial={{ scale: 0, opacity: 1 }}
                  animate={{ scale: [0, 2, 0], opacity: [1, 0.8, 0] }}
                  transition={{ duration: 0.4, ease: 'easeOut' }}
                  style={{
                    position: 'absolute',
                    width: 20,
                    height: 20,
                    background: 'radial-gradient(circle, #ff4444, #ff0000)',
                    borderRadius: '50%',
                    left: 40,
                    top: 40
                  }}
                />
                {/* Explosion particles */}
                {Array.from({ length: 8 }).map((_, i) => (
                  <motion.div
                    key={i}
                    initial={{
                      x: 50,
                      y: 50,
                      scale: 0,
                      opacity: 1
                    }}
                    animate={{
                      x: 50 + Math.cos(i * Math.PI / 4) * 30,
                      y: 50 + Math.sin(i * Math.PI / 4) * 30,
                      scale: [0, 1, 0],
                      opacity: [1, 0.8, 0]
                    }}
                    transition={{ duration: 0.4, ease: 'easeOut' }}
                    style={{
                      position: 'absolute',
                      width: 6,
                      height: 6,
                      background: '#ff6600',
                      borderRadius: '50%'
                    }}
                  />
                ))}
                {/* Spark particles */}
                {Array.from({ length: 12 }).map((_, i) => (
                  <motion.div
                    key={`spark-${i}`}
                    initial={{
                      x: 50,
                      y: 50,
                      scale: 0,
                      opacity: 1
                    }}
                    animate={{
                      x: 50 + Math.cos(i * Math.PI / 6) * 25,
                      y: 50 + Math.sin(i * Math.PI / 6) * 25,
                      scale: [0, 0.5, 0],
                      opacity: [1, 0.6, 0]
                    }}
                    transition={{ duration: 0.3, ease: 'easeOut', delay: Math.random() * 0.1 }}
                    style={{
                      position: 'absolute',
                      width: 3,
                      height: 3,
                      background: '#ffff00',
                      borderRadius: '50%'
                    }}
                  />
                ))}
              </div>
            )
          }

          return null
        })}
      </AnimatePresence>
    </div>
  )
}