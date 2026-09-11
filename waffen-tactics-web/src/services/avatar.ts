export function buildDiscordAvatarUrl(
  userId: string | number | null | undefined,
  avatarHash: string | null | undefined,
  size = 256,
): string | null {
  const normalizedUserId = String(userId ?? '').trim()
  const normalizedHash = typeof avatarHash === 'string' ? avatarHash.trim() : ''
  if (!normalizedUserId || !normalizedHash) return null

  return `https://cdn.discordapp.com/avatars/${encodeURIComponent(normalizedUserId)}/${encodeURIComponent(normalizedHash)}.png?size=${size}`
}
