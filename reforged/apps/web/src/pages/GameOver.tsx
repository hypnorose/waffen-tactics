import type { RunState } from '@reforged/schema';

export function GameOver({ run, onNewRun }: { run: RunState; onNewRun: () => void }) {
  return (
    <div className="game-over">
      <h1>{run.status === 'won' ? '🏆 Zwycięstwo rankingowe!' : '💀 Koniec run'}</h1>
      <p>
        Wygrane: {run.wins} · Porażki: {run.losses}
      </p>
      <button type="button" onClick={onNewRun}>Zacznij nowy run</button>
    </div>
  );
}
