export const config = {
  port: Number(process.env.PORT ?? 8080),
  host: process.env.HOST ?? '0.0.0.0',
  dbFile: process.env.DB_FILE ?? 'reforged.sqlite3',
  jwtSecret: process.env.JWT_SECRET ?? 'dev-secret-change-me',
};
