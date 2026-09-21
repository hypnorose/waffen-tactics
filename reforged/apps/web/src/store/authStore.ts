import { create } from 'zustand';
import type { UserProfile } from '@reforged/schema';
import { api, ApiError, setToken } from '../services/api.js';

const STORAGE_KEY = 'reforged.token';
const DISCORD_CLIENT_ID = import.meta.env.VITE_DISCORD_CLIENT_ID ?? '';

function redirectUri(): string {
  return `${window.location.origin}/auth/callback`;
}

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStoredToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(STORAGE_KEY, token);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // best-effort only — auth still works for the current tab via in-memory token
  }
}

interface AuthState {
  token: string | null;
  profile: UserProfile | null;
  error: string | null;
  loading: boolean;
  loginWithDiscord: () => void;
  completeDiscordCallback: (code: string) => Promise<void>;
  refreshProfile: () => Promise<void>;
  logout: () => void;
}

const initialToken = readStoredToken();
setToken(initialToken);

export const useAuthStore = create<AuthState>((set) => ({
  token: initialToken,
  profile: null,
  error: null,
  loading: false,

  loginWithDiscord: () => {
    if (!DISCORD_CLIENT_ID) {
      set({ error: 'Brak skonfigurowanego VITE_DISCORD_CLIENT_ID' });
      return;
    }
    const url = `https://discord.com/api/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&redirect_uri=${encodeURIComponent(redirectUri())}&response_type=code&scope=identify`;
    window.location.href = url;
  },

  completeDiscordCallback: async (code) => {
    set({ loading: true, error: null });
    try {
      const { token, profile } = await api.exchangeDiscordCode(code);
      setToken(token);
      writeStoredToken(token);
      set({ token, profile, loading: false });
    } catch (err) {
      set({ error: err instanceof ApiError ? err.message : String(err), loading: false });
    }
  },

  refreshProfile: async () => {
    try {
      const profile = await api.getMe();
      set({ profile });
    } catch {
      // non-fatal — header just won't update until the next successful refresh
    }
  },

  logout: () => {
    setToken(null);
    writeStoredToken(null);
    set({ token: null, profile: null });
  },
}));
