import { useEffect, useRef, useState } from 'react';
import type { LeaderboardEntry } from '@reforged/schema';
import { api } from '../../services/api.js';
import { RankBadge } from './RankBadge.js';

interface Props {
  currentUsername: string;
}

function placementLabel(index: number): string {
  if (index === 0) return '🥇';
  if (index === 1) return '🥈';
  if (index === 2) return '🥉';
  return `#${index + 1}`;
}

function avatarFallback(username: string): string {
  return username.slice(0, 1).toUpperCase();
}

export function LeaderboardPanel({ currentUsername }: Props) {
  const [open, setOpen] = useState(false);
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  async function loadLeaderboard() {
    setLoading(true);
    setError(false);
    try {
      setEntries(await api.getLeaderboard());
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadLeaderboard();
  }, []);

  useEffect(() => {
    if (!open) return;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    closeRef.current?.focus();
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open]);

  return (
    <>
      <div className="leaderboard-launcher">
        <button
          ref={triggerRef}
          type="button"
          className="leaderboard-toggle"
          aria-haspopup="dialog"
          aria-expanded={open}
          onClick={() => setOpen(true)}
        >
          🏆 Ranking graczy
        </button>
      </div>

      {open && (
        <div className="leaderboard-modal-backdrop" role="presentation" onMouseDown={() => setOpen(false)}>
          <section
            className="leaderboard-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="leaderboard-title"
            aria-busy={loading}
            onMouseDown={(event) => event.stopPropagation()}
          >
      <div className="leaderboard-heading">
        <div>
          <h2 id="leaderboard-title">Ranking graczy</h2>
          <p>Top 20 według ELO</p>
        </div>
        <div className="leaderboard-heading-actions">
          <span className="leaderboard-live-dot" title="Ranking pobierany na żywo" aria-label="Ranking pobierany na żywo" />
          <button
            ref={closeRef}
            type="button"
            className="leaderboard-close"
            aria-label="Zamknij ranking"
            onClick={() => setOpen(false)}
          >
            ×
          </button>
        </div>
      </div>

      {loading && <p className="leaderboard-message">Ładowanie rankingu...</p>}
      {!loading && error && (
        <div className="leaderboard-message">
          <p>Nie udało się pobrać rankingu.</p>
          <button type="button" onClick={() => void loadLeaderboard()}>
            Spróbuj ponownie
          </button>
        </div>
      )}
      {!loading && !error && entries.length === 0 && <p className="leaderboard-message">Brak zarejestrowanych graczy.</p>}

      {!loading && !error && entries.length > 0 && (
        <ol className="leaderboard-list">
          {entries.map((entry, index) => {
            const isCurrentPlayer = entry.username === currentUsername;
            return (
              <li key={`${entry.username}-${index}`} className={`leaderboard-entry${isCurrentPlayer ? ' is-current-player' : ''}`}>
                <span className="leaderboard-placement" aria-label={`Pozycja ${index + 1}`}>
                  {placementLabel(index)}
                </span>
                {entry.avatarUrl ? (
                  <img className="leaderboard-avatar" src={entry.avatarUrl} alt="" />
                ) : (
                  <span className="leaderboard-avatar leaderboard-avatar-fallback">{avatarFallback(entry.username)}</span>
                )}
                <div className="leaderboard-player">
                  <div className="leaderboard-player-name">
                    <span>{entry.username}</span>
                    {isCurrentPlayer && <span className="leaderboard-you">Ty</span>}
                  </div>
                  <RankBadge rank={entry.rank} />
                </div>
              </li>
            );
          })}
        </ol>
      )}
          </section>
        </div>
      )}
    </>
  );
}
