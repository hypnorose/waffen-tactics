/**
 * Player-facing login copy lives outside the page component so the branding
 * can be localized or revised without coupling content to layout.
 */
export const loginCopy = {
  brandName: 'WAFFEN TACTICS',
  setName: 'SET 2: ŚWIT NOWOCIOT',
  accessibleBrandName: 'Waffen Tactics, Set 2: Świt Nowociot',
  description: 'Strategiczna gra auto-battler w stylu TFT',
  discordLogin: 'Zaloguj się przez Discord',
  missingDiscordConfig: 'Brak konfiguracji logowania przez Discord. Sprawdź `VITE_DISCORD_CLIENT_ID` w frontendowym `.env`.',
  footer: 'Strategiczny auto-battler',
} as const
