import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const API_URL = window.location.hostname === 'localhost' 
  ? 'http://localhost:8000' 
  : (import.meta.env.VITE_API_URL || 'https://waffentactics.pl/api')

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  console.log('🔐 API Request:', config.method?.toUpperCase(), config.url, 'Token present:', !!token)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
    console.log('🔐 Added Authorization header')
  }
  return config
})

// Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const authAPI = {
  exchangeCode: (code: string) => 
    api.post('/auth/exchange', { code }),
  
  getMe: () => 
    api.get('/auth/me'),
}

export const gameAPI = {
  getPlayerState: () => 
    api.get('/game/state'),
  
  startGame: () => 
    api.post('/game/start'),
  
  buyUnit: (unitId: string) => 
    api.post('/game/buy', { unit_id: unitId }),
  
  sellUnit: (instanceId: string) => 
    api.post('/game/sell', { instance_id: instanceId }),
  
  moveToBoard: (instanceId: string) => 
    api.post('/game/move-to-board', { instance_id: instanceId }),
  
  moveToBench: (instanceId: string) => 
    api.post('/game/move-to-bench', { instance_id: instanceId }),
  
  rerollShop: () => 
    api.post('/game/reroll'),
  
  buyXP: () => 
    api.post('/game/buy-xp'),
  
  toggleShopLock: () => 
    api.post('/game/toggle-lock'),
  
  startCombat: () => 
    api.post('/game/combat'),
  
  resetGame: () => 
    api.post('/game/reset'),
  
  surrender: () => 
    api.post('/game/surrender'),
  
  getLeaderboard: () => 
    api.get('/game/leaderboard'),
  
  getUnits: () => 
    api.get('/game/units'),
  
  getTraits: () => 
    api.get('/game/traits'),
}

export default api
