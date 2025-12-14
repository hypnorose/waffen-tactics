import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  username: string
  discriminator: string
  avatar: string
}

interface AuthState {
  user: User | null
  token: string | null
  hydrated: boolean
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  setHydrated: () => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      hydrated: false,
      setUser: (user) => set({ user }),
      setToken: (token) => set({ token }),
      setHydrated: () => set({ hydrated: true }),
      logout: () => set({ user: null, token: null }),
    }),
    {
      name: 'auth-storage',
      onRehydrateStorage: () => (state) => {
        state?.setHydrated()
      },
    }
  )
)
