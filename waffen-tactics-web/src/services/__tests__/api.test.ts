import { afterEach, describe, expect, it, vi } from 'vitest'
import api, { gameAPI } from '../api'

describe('game API mutation identity', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('sends a fresh idempotency key for each new user intent', async () => {
    const post = vi.spyOn(api, 'post').mockResolvedValue({ data: { state: {} } } as any)

    await gameAPI.buyUnit('unit-a')
    await gameAPI.buyUnit('unit-a')

    expect(post).toHaveBeenCalledTimes(2)
    const firstConfig = post.mock.calls[0][2] as any
    const secondConfig = post.mock.calls[1][2] as any
    expect(firstConfig.headers['Idempotency-Key']).toEqual(expect.any(String))
    expect(secondConfig.headers['Idempotency-Key']).toEqual(expect.any(String))
    expect(firstConfig.headers['Idempotency-Key']).not.toBe(secondConfig.headers['Idempotency-Key'])
  })

  it('shares one in-flight request when a retry reuses the same key', async () => {
    const post = vi.spyOn(api, 'post').mockResolvedValue({ data: { state: {} } } as any)
    const options = { idempotencyKey: 'intent-123' }

    const first = gameAPI.combineItem('spices', 'safe', options)
    const retry = gameAPI.combineItem('spices', 'safe', options)

    expect(retry).toBe(first)
    await Promise.all([first, retry])
    expect(post).toHaveBeenCalledOnce()
    expect((post.mock.calls[0][2] as any).headers['Idempotency-Key']).toBe('intent-123')
  })

  it('serializes different player-state mutations so responses cannot arrive out of order', async () => {
    let resolveFirst: ((value: any) => void) | undefined
    const firstResponse = new Promise(resolve => { resolveFirst = resolve })
    const post = vi.spyOn(api, 'post')
      .mockReturnValueOnce(firstResponse as any)
      .mockResolvedValueOnce({ data: { state: {} } } as any)

    const first = gameAPI.buyXP({ idempotencyKey: 'intent-first' })
    const second = gameAPI.rerollShop({ idempotencyKey: 'intent-second' })
    await Promise.resolve()
    await Promise.resolve()

    expect(post).toHaveBeenCalledOnce()
    resolveFirst!({ data: { state: {} } })
    await Promise.all([first, second])

    expect(post).toHaveBeenCalledTimes(2)
    expect((post.mock.calls[0][2] as any).headers['Idempotency-Key']).toBe('intent-first')
    expect((post.mock.calls[1][2] as any).headers['Idempotency-Key']).toBe('intent-second')
  })

  it('can repeat a completed request with the same key and let the backend return its cached result', async () => {
    const post = vi.spyOn(api, 'post').mockResolvedValue({ data: { state: {} } } as any)
    const options = { idempotencyKey: 'intent-retry-after-timeout' }

    await gameAPI.sellUnit('instance-a', options)
    await gameAPI.sellUnit('instance-a', options)

    expect(post).toHaveBeenCalledTimes(2)
    expect((post.mock.calls[0][2] as any).headers['Idempotency-Key']).toBe(options.idempotencyKey)
    expect((post.mock.calls[1][2] as any).headers['Idempotency-Key']).toBe(options.idempotencyKey)
  })
})
