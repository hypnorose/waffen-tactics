import { useEffect, useRef } from 'react';
import { useAuthStore } from '../store/authStore.js';

export function AuthCallback() {
  const { completeDiscordCallback, error } = useAuthStore();
  const attempted = useRef(false);

  useEffect(() => {
    if (attempted.current) return;
    attempted.current = true;

    const code = new URLSearchParams(window.location.search).get('code');
    if (!code) {
      window.location.replace('/');
      return;
    }
    completeDiscordCallback(code).then(() => {
      window.history.replaceState({}, '', '/');
    });
  }, [completeDiscordCallback]);

  return (
    <div className="auth-panel">
      {error ? (
        <>
          <p className="error">{error}</p>
          <button type="button" onClick={() => window.location.replace('/')}>
            Wróć do logowania
          </button>
        </>
      ) : (
        <p>Logowanie przez Discord...</p>
      )}
    </div>
  );
}
