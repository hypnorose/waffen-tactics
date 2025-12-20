import { createContext, useContext, useState, useCallback, ReactNode } from 'react'

interface HurtEffect {
  id: string
  unitId: string
  type: 'shake' | 'flash' | 'explosion'
  timestamp: number
}

interface HurtEffectsContextType {
  activeEffects: HurtEffect[]
  triggerHurt: (unitId: string, type?: 'shake' | 'flash' | 'explosion') => void
}

const HurtEffectsContext = createContext<HurtEffectsContextType | null>(null)

export function HurtEffectsProvider({ children }: { children: ReactNode }) {
  const [activeEffects, setActiveEffects] = useState<HurtEffect[]>([])

  const triggerHurt = useCallback((unitId: string, type: 'shake' | 'flash' | 'explosion' = 'flash') => {
    const effect: HurtEffect = {
      id: `${unitId}-${Date.now()}-${Math.random()}`,
      unitId,
      type,
      timestamp: Date.now()
    }

    setActiveEffects(prev => [...prev, effect])

    // Auto-remove effect after animation duration
    setTimeout(() => {
      setActiveEffects(prev => prev.filter(e => e.id !== effect.id))
    }, 400) // Match animation duration
  }, [])

  return (
    <HurtEffectsContext.Provider value={{ activeEffects, triggerHurt }}>
      {children}
    </HurtEffectsContext.Provider>
  )
}

export function useHurtEffects() {
  const context = useContext(HurtEffectsContext)
  if (!context) {
    throw new Error('useHurtEffects must be used within HurtEffectsProvider')
  }
  return context
}