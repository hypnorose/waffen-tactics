import { config } from '../config.js';

export interface DiscordUser {
  id: string;
  username: string;
  avatarHash: string | null;
}

export class DiscordAuthError extends Error {}

export async function exchangeDiscordCode(code: string): Promise<DiscordUser> {
  const tokenRes = await fetch('https://discord.com/api/oauth2/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: config.discord.clientId,
      client_secret: config.discord.clientSecret,
      grant_type: 'authorization_code',
      code,
      redirect_uri: config.discord.redirectUri,
    }),
  });
  if (!tokenRes.ok) throw new DiscordAuthError('token_exchange_failed');
  const tokenData = (await tokenRes.json()) as { access_token: string };

  const userRes = await fetch('https://discord.com/api/users/@me', {
    headers: { Authorization: `Bearer ${tokenData.access_token}` },
  });
  if (!userRes.ok) throw new DiscordAuthError('user_fetch_failed');
  const userData = (await userRes.json()) as { id: string; username: string; avatar: string | null };

  return { id: userData.id, username: userData.username, avatarHash: userData.avatar };
}

export function discordAvatarUrl(user: { id: string; avatarHash: string | null }): string | null {
  if (!user.avatarHash) return null;
  return `https://cdn.discordapp.com/avatars/${user.id}/${user.avatarHash}.png?size=128`;
}
