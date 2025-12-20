import React, { createContext, useContext, useState, useCallback, useRef } from 'react'

export type Projectile = {
  id: string
  emoji: string
  fromId: string
  toId: string
  duration: number
  createdAt: number
  onComplete?: () => void
}

interface ProjectileContextValue {
  projectiles: Projectile[]
  spawnProjectile: (opts: { fromId: string; toId: string; emoji?: string; duration?: number; onComplete?: () => void }) => void
}

const ProjectileContext = createContext<ProjectileContextValue | null>(null)

export function ProjectileProvider({ children }: { children: React.ReactNode }) {
  const [projectiles, setProjectiles] = useState<Projectile[]>([])
  const timers = useRef<Record<string, number>>({})

  const spawnProjectile = useCallback(({ fromId, toId, emoji = '💥', duration = 350, onComplete }: { fromId: string; toId: string; emoji?: string; duration?: number; onComplete?: () => void }) => {
    const id = `${Date.now().toString(36)}_${Math.random().toString(36).slice(2,9)}`
    const p: Projectile = { id, emoji, fromId, toId, duration, createdAt: Date.now(), onComplete }
    setProjectiles(prev => [...prev, p])
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
    <ProjectileContext.Provider value={{ projectiles, spawnProjectile }}>
      {children}
    </ProjectileContext.Provider>
  )
}

export function useProjectileSystem() {
  const ctx = useContext(ProjectileContext)
  if (!ctx) throw new Error('useProjectileSystem must be used within ProjectileProvider')
  return ctx
}
