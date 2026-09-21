export const config = {
  port: Number(process.env.PORT ?? 8080),
  host: process.env.HOST ?? '0.0.0.0',
  dbFile: process.env.DB_FILE ?? 'reforged.sqlite3',
  jwtSecret: process.env.JWT_SECRET ?? 'dev-secret-change-me',
  discord: {
    clientId: process.env.DISCORD_CLIENT_ID ?? '',
    clientSecret: process.env.DISCORD_CLIENT_SECRET ?? '',
    redirectUri: process.env.DISCORD_REDIRECT_URI ?? 'http://localhost:5173/auth/callback',
  },
};
