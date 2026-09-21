import { useState } from 'react';
import { useAuthStore } from '../../store/authStore.js';

export function AuthPanel() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const { login, register, loading, error } = useAuthStore();

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (mode === 'login') login(email, password);
    else register(email, password);
  }

  return (
    <div className="auth-panel">
      <h1>Waffen Tactics: Reforged</h1>
      <form onSubmit={submit}>
        <input type="email" placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input
          type="password"
          placeholder="hasło (min. 8 znaków)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={8}
          required
        />
        <button type="submit" disabled={loading}>
          {mode === 'login' ? 'Zaloguj' : 'Zarejestruj'}
        </button>
      </form>
      <button type="button" className="link" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
        {mode === 'login' ? 'Nie masz konta? Zarejestruj się' : 'Masz już konto? Zaloguj się'}
      </button>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
