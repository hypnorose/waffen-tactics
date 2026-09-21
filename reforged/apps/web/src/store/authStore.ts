import { create } from 'zustand';
import { api, setToken } from '../services/api.js';

const STORAGE_KEY = 'reforged.token';

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
  error: string | null;
  loading: boolean;
  register: (email: string, password: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const initialToken = readStoredToken();
setToken(initialToken);

export const useAuthStore = create<AuthState>((set) => ({
  token: initialToken,
  error: null,
  loading: false,

  register: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const { token } = await api.register(email, password);
      setToken(token);
      writeStoredToken(token);
      set({ token, loading: false });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false });
    }
  },

  login: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const { token } = await api.login(email, password);
      setToken(token);
      writeStoredToken(token);
      set({ token, loading: false });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false });
    }
  },

  logout: () => {
    setToken(null);
    writeStoredToken(null);
    set({ token: null });
  },
}));
