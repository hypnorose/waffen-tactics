import { useEffect, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8080';

interface UnitSummary {
  id: string;
  name: string;
  tags: string[];
  emoji: string;
}

export function App() {
  const [units, setUnits] = useState<UnitSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/content/units`)
      .then((res) => res.json())
      .then(setUnits)
      .catch((err) => setError(String(err)));
  }, []);

  return (
    <main style={{ fontFamily: 'sans-serif', padding: '2rem' }}>
      <h1>Waffen Tactics: Reforged</h1>
      <p>Faza 0 — szkielet monorepo. Poniżej roster wczytany z serwera (@reforged/server → @reforged/content-data):</p>
      {error && <p style={{ color: 'crimson' }}>Błąd: {error}</p>}
      {!units && !error && <p>Ładowanie...</p>}
      {units && (
        <ul>
          {units.map((unit) => (
            <li key={unit.id}>
              {unit.emoji} {unit.name} — {unit.tags.join(', ')}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
