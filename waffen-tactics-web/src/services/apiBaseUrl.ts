const configuredApiUrl = typeof import.meta.env.VITE_API_URL === 'string'
  ? import.meta.env.VITE_API_URL.trim()
  : ''

const hostname = typeof window !== 'undefined' ? window.location.hostname : ''
const isLocalDevelopment = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1'

// Keep every browser transport on the same explicit API contract. Local Vite
// development talks to the local backend; production uses the current origin
// unless deployment provides VITE_API_URL.
export const API_BASE_URL = configuredApiUrl || (
  isLocalDevelopment
    ? 'http://localhost:8000'
    : (typeof window !== 'undefined' ? window.location.origin : 'https://waffentactics.pl')
)
