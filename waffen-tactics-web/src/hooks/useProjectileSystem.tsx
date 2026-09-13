import React, { createContext, useContext, useState, useCallback, useRef } from 'react'

export type Projectile = {
  id: string
  emoji: string
  fromId: string
  toId: string
  duration: number
  createdAt: number
  sourceEventId?: string
  sourceSeq?: number
  onComplete?: () => void
}

interface ProjectileContextValue {
  projectiles: Projectile[]
  spawnProjectile: (opts: { id?: string; fromId: string; toId: string; emoji?: string; duration?: number; sourceEventId?: string; sourceSeq?: number; onComplete?: () => void }) => void
  clearProjectiles: () => void
}

const ProjectileContext = createContext<ProjectileContextValue | null>(null)

export function ProjectileProvider({ children }: { children: React.ReactNode }) {
  const [projectiles, setProjectiles] = useState<Projectile[]>([])
  const timers = useRef<Record<string, number>>({})

  const clearProjectiles = useCallback(() => {
    Object.values(timers.current).forEach(id => clearTimeout(id))
    timers.current = {}
    setProjectiles([])
  }, [])

  const spawnProjectile = useCallback(({ id: requestedId, fromId, toId, emoji = '💥', duration = 350, sourceEventId, sourceSeq, onComplete }: { id?: string; fromId: string; toId: string; emoji?: string; duration?: number; sourceEventId?: string; sourceSeq?: number; onComplete?: () => void }) => {
    const id = requestedId || `${Date.now().toString(36)}_${Math.random().toString(36).slice(2,9)}`
    if (Object.prototype.hasOwnProperty.call(timers.current, id)) {
      console.debug('[PROJECTILE] duplicate ignored', { id, fromId, toId })
      return
    }
    const p: Projectile = { id, emoji, fromId, toId, duration, createdAt: Date.now(), sourceEventId, sourceSeq, onComplete }
    setProjectiles(prev => [...prev, p])
    console.debug('[PROJECTILE] spawn', { id, fromId, toId, emoji, duration })
    const t = window.setTimeout(() => {
      setProjectiles(prev => prev.filter(pp => pp.id !== id))
      delete timers.current[id]
      // Call completion callback
      if (p.onComplete) {
        p.onComplete()
      }
    }, duration + 50)
    timers.current[id] = t
  }, [])

  // cleanup on unmount
  React.useEffect(() => {
    return () => {
      Object.values(timers.current).forEach(id => clearTimeout(id))
      timers.current = {}
    }
  }, [])

  return (
    <ProjectileContext.Provider value={{ projectiles, spawnProjectile, clearProjectiles }}>
      {children}
    </ProjectileContext.Provider>
  )
}

export function useProjectileSystem() {
  const ctx = useContext(ProjectileContext)
  if (!ctx) throw new Error('useProjectileSystem must be used within ProjectileProvider')
  return ctx
}
