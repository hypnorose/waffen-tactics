import axios from 'axios'
import { useAuthStore } from '../store/authStore'
import { API_BASE_URL } from './apiBaseUrl'
import { createIdempotencyKey } from './requestIdentity'
import type { MutationRequestOptions } from './requestIdentity'

const api = axios.create({
  baseURL: API_BASE_URL,
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

const mutationTails = new Map<string, Promise<unknown>>()
const inFlightMutations = new Map<string, Promise<any>>()

function postMutation<T = any>(url: string, data: unknown, options?: MutationRequestOptions) {
  const idempotencyKey = options?.idempotencyKey?.trim() || createIdempotencyKey()
  const resourceKey = 'player-state'
  const requestIdentity = `${resourceKey}:${idempotencyKey}`
  const existing = inFlightMutations.get(requestIdentity)
  if (existing) return existing

  const previous = mutationTails.get(resourceKey) || Promise.resolve()
  const request = previous
    .catch(() => undefined)
    .then(() => api.post<T>(url, data, { headers: { 'Idempotency-Key': idempotencyKey } }))

  let trackedRequest: Promise<any>
  trackedRequest = request.finally(() => {
    if (inFlightMutations.get(requestIdentity) === trackedRequest) {
      inFlightMutations.delete(requestIdentity)
    }
  })
  inFlightMutations.set(requestIdentity, trackedRequest)

  const serializedTail = trackedRequest.then(() => undefined, () => undefined)
  mutationTails.set(resourceKey, serializedTail)
  void serializedTail.finally(() => {
    if (mutationTails.get(resourceKey) === serializedTail) mutationTails.delete(resourceKey)
  })

  return trackedRequest
}

export const authAPI = {
  exchangeCode: (code: string) => 
    api.post('/auth/exchange', { code }),
  
  getMe: () => 
    api.get('/auth/me'),
}

export const gameAPI = {
  getPlayerState: () => 
    api.get('/game/state'),
  
  startGame: (options?: MutationRequestOptions) =>
    postMutation('/game/start', undefined, options),
  
  buyUnit: (unitId: string, options?: MutationRequestOptions) =>
    postMutation('/game/buy', { unit_id: unitId }, options),
  
  sellUnit: (instanceId: string, options?: MutationRequestOptions) =>
    postMutation('/game/sell', { instance_id: instanceId }, options),
  
  moveToBoard: (instanceId: string, position: 'front' | 'back' = 'front', options?: MutationRequestOptions) =>
    postMutation('/game/move-to-board', { instance_id: instanceId, position }, options),
  
  switchLine: (instanceId: string, position: 'front' | 'back', options?: MutationRequestOptions) =>
    postMutation('/game/switch-line', { instance_id: instanceId, position }, options),
  
  moveToBench: (instanceId: string, options?: MutationRequestOptions) =>
    postMutation('/game/move-to-bench', { instance_id: instanceId }, options),
  
  rerollShop: (options?: MutationRequestOptions) =>
    postMutation('/game/reroll', undefined, options),
  
  buyXP: (options?: MutationRequestOptions) =>
    postMutation('/game/buy-xp', undefined, options),
  
  toggleShopLock: (options?: MutationRequestOptions) =>
    postMutation('/game/toggle-lock', undefined, options),
  
  startCombat: (options?: MutationRequestOptions) =>
    postMutation('/game/combat', undefined, options),
  
  resetGame: (options?: MutationRequestOptions) =>
    postMutation('/game/reset', undefined, options),
  
  surrender: (options?: MutationRequestOptions) =>
    postMutation('/game/surrender', undefined, options),
  
  getLeaderboard: (period: string = '24h') =>
    api.get('/game/leaderboard', { params: { period } }),
  
  getUnits: () => 
    api.get('/game/units'),
  
  getTraits: () => 
    api.get('/game/traits'),
  getItems: () => api.get('/game/items'),
  equipItem: (instanceId: string, itemId: string, options?: MutationRequestOptions) =>
    postMutation('/game/equip-item', { instance_id: instanceId, item_id: itemId }, options),
  combineItem: (firstItem: string, secondItem: string, options?: MutationRequestOptions) =>
    postMutation('/game/combine-item', { first_item: firstItem, second_item: secondItem }, options),
  ensurePlayerAvatar: (payload?: { avatarUrl?: string }, options?: MutationRequestOptions) =>
    postMutation('/game/player-avatar', payload || {}, options),
}

export default api
