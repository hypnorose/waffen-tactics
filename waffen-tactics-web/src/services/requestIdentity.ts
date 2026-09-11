export interface MutationRequestOptions {
  // Reuse this exact key when retrying one user intent after a timeout.
  idempotencyKey?: string
}

export function createIdempotencyKey(prefix = 'client'): string {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return `${prefix}:${globalThis.crypto.randomUUID()}`
  }
  return `${prefix}:${Date.now().toString(36)}:${Math.random().toString(36).slice(2)}`
}
