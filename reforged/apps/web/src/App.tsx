import { useEffect } from 'react';
import { useAuthStore } from './store/authStore.js';
import { useRunStore } from './store/runStore.js';
import { AuthPanel } from './components/auth/AuthPanel.js';
import { Run } from './pages/Run.js';

export function App() {
  const token = useAuthStore((s) => s.token);
  const units = useRunStore((s) => s.units);
  const loadContent = useRunStore((s) => s.loadContent);
  const loadOrCreateRun = useRunStore((s) => s.loadOrCreateRun);

  useEffect(() => {
    if (!token) return;
    loadContent();
    loadOrCreateRun();
  }, [token]);

  if (!token) return <AuthPanel />;
  if (Object.keys(units).length === 0) return <p className="loading">Ładowanie zawartości...</p>;

  return <Run />;
}
