import { describe, expect, it } from 'vitest'
import { buildDiscordAvatarUrl } from '../avatar'

describe('buildDiscordAvatarUrl', () => {
  it('builds a CDN URL for a custom Discord avatar', () => {
    expect(buildDiscordAvatarUrl('42', 'hash', 128)).toBe(
      'https://cdn.discordapp.com/avatars/42/hash.png?size=128',
    )
  })

  it.each([
    [null, 'hash'],
    ['42', null],
    ['42', ''],
    ['42', '   '],
  ])('returns no URL when Discord has no custom avatar', (userId, avatarHash) => {
    expect(buildDiscordAvatarUrl(userId, avatarHash)).toBeNull()
  })

  it('encodes path segments instead of interpolating untrusted values', () => {
    expect(buildDiscordAvatarUrl('user/id', 'hash/value')).toBe(
      'https://cdn.discordapp.com/avatars/user%2Fid/hash%2Fvalue.png?size=256',
    )
  })
})
