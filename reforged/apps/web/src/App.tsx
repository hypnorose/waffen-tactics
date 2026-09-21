import { useEffect } from 'react';
import { useAuthStore } from './store/authStore.js';
import { useRunStore } from './store/runStore.js';
import { AuthPanel } from './components/auth/AuthPanel.js';
import { AuthCallback } from './pages/AuthCallback.js';
import { PlayerHeader } from './components/profile/PlayerHeader.js';
import { Run } from './pages/Run.js';

const isAuthCallback = window.location.pathname === '/auth/callback';

export function App() {
  const token = useAuthStore((s) => s.token);
  const profile = useAuthStore((s) => s.profile);
  const refreshProfile = useAuthStore((s) => s.refreshProfile);
  const units = useRunStore((s) => s.units);
  const run = useRunStore((s) => s.run);
  const loadContent = useRunStore((s) => s.loadContent);
  const loadOrCreateRun = useRunStore((s) => s.loadOrCreateRun);

  useEffect(() => {
    if (!token || isAuthCallback) return;
    loadContent();
    loadOrCreateRun();
    refreshProfile();
  }, [token]);

  if (isAuthCallback) return <AuthCallback />;
  if (!token) return <AuthPanel />;
  if (Object.keys(units).length === 0 || !profile) return <p className="loading">Ładowanie...</p>;

  return (
    <div className="app-shell">
      <PlayerHeader profile={profile} run={run} />
      <Run />
    </div>
  );
}
