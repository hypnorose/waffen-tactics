import React, { createContext, useContext, useRef, useCallback } from 'react'

type AnchorMap = Record<string, HTMLDivElement | null>

interface UnitAnchorsContextValue {
  register: (id: string, el: HTMLDivElement | null) => void
  getCenter: (id: string, relativeTo?: Element | null) => { x: number; y: number } | null
}

const UnitAnchorsContext = createContext<UnitAnchorsContextValue | null>(null)

export function UnitAnchorsProvider({ children }: { children: React.ReactNode }) {
  const refs = useRef<AnchorMap>({})

  const register = useCallback((id: string, el: HTMLDivElement | null) => {
    refs.current[id] = el
  }, [])

  const getCenter = useCallback((id: string, relativeTo: Element | null = null) => {
    const el = refs.current[id]
    if (!el) return null
    const rect = el.getBoundingClientRect()
    if (relativeTo) {
      const parentRect = relativeTo.getBoundingClientRect()
      return { x: rect.left + rect.width / 2 - parentRect.left, y: rect.top + rect.height / 2 - parentRect.top }
    }
    return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 }
  }, [])

  return (
    <UnitAnchorsContext.Provider value={{ register, getCenter }}>
      {children}
    </UnitAnchorsContext.Provider>
  )
}

export function useUnitAnchors() {
  const ctx = useContext(UnitAnchorsContext)
  if (!ctx) throw new Error('useUnitAnchors must be used within UnitAnchorsProvider')
  return ctx
}
