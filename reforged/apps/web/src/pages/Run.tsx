import { DndContext, type DragEndEvent } from '@dnd-kit/core';
import { useAuthStore } from '../store/authStore.js';
import { useRunStore } from '../store/runStore.js';
import { Board3x3 } from '../components/board/Board3x3.js';
import { BenchPanel } from '../components/shop/BenchPanel.js';
import { ShopPanel } from '../components/shop/ShopPanel.js';
import { AugmentPicker } from '../components/augment/AugmentPicker.js';
import { AugmentRow } from '../components/augment/AugmentRow.js';
import { CombatReplayViewer } from '../components/combat/CombatReplayViewer.js';
import { GameOver } from './GameOver.js';

const CELL_ID_PATTERN = /^cell-(\d)-(\d)$/;

export function Run() {
  const {
    run,
    units,
    augments,
    buy,
    sell,
    reroll,
    toggleLock,
    buyLevel,
    place,
    bench,
    pickAugment,
    startCombat,
    loadOrCreateRun,
    startNewRun,
    surrenderRun,
    lastCombat,
    loading,
    error,
  } = useRunStore();
  const profile = useAuthStore((s) => s.profile);

  function handleStartNewRun() {
    if (window.confirm('Czy na pewno chcesz zacząć od nowa? Obecna rozgrywka zostanie poddana.')) {
      startNewRun();
    }
  }

  if (!run) {
    if (loading) return <p className="loading">Ładowanie rozgrywki...</p>;

    return (
      <section className="run-recovery" aria-live="polite">
        <h1>Nie udało się załadować rozgrywki</h1>
        {error && <p className="error">{error}</p>}
        <div className="run-recovery-actions">
          <button type="button" onClick={loadOrCreateRun} disabled={loading}>
            Spróbuj ponownie
          </button>
          <button type="button" className="fight-button" onClick={handleStartNewRun} disabled={loading}>
            Zacznij od nowa
          </button>
        </div>
      </section>
    );
  }

  if (run.status !== 'active' && !lastCombat) {
    return <GameOver run={run} onNewRun={startNewRun} />;
  }

  function handleDragEnd(event: DragEndEvent) {
    const instanceId = String(event.active.id);
    const overId = event.over ? String(event.over.id) : undefined;
    if (!overId) return;

    if (overId === 'bench') {
      bench(instanceId);
      return;
    }
    const match = CELL_ID_PATTERN.exec(overId);
    if (match) {
      place(instanceId, { row: Number(match[1]), col: Number(match[2]) });
    }
  }

  return (
    <div className="run-page">
      <DndContext onDragEnd={handleDragEnd}>
        <Board3x3 run={run} units={units} />
        <BenchPanel run={run} units={units} onSell={sell} />
      </DndContext>

      <ShopPanel run={run} units={units} onBuy={buy} onReroll={reroll} onToggleLock={toggleLock} onBuyLevel={buyLevel} />

      <AugmentRow augmentIds={run.augmentsPicked} augments={augments} label="Twoje perki:" />

      <div className="run-actions">
        <button className="fight-button" onClick={startCombat} disabled={loading}>
          ⚔️ Rozpocznij walkę
        </button>
        {run.status === 'active' && (
          <button
            type="button"
            className="surrender-button"
            onClick={() => {
              if (window.confirm('Czy na pewno chcesz poddać tę rozgrywkę?')) surrenderRun();
            }}
            disabled={loading}
          >
            Poddaj rozgrywkę
          </button>
        )}
        {error && <p className="error">{error}</p>}
      </div>

      {run.augmentPending && <AugmentPicker runId={run.runId} onPick={pickAugment} />}

      {lastCombat && profile && (
        <CombatReplayViewer
          combatLog={lastCombat.combatLog}
          units={units}
          augments={augments}
          playerName={profile.username}
          playerAvatarUrl={profile.avatarUrl}
          playerAugmentIds={run.augmentsPicked}
          opponentName={lastCombat.opponentName}
          opponentAvatarUrl={lastCombat.opponentAvatarUrl}
          opponentAugmentIds={lastCombat.opponentAugmentsPicked}
          onClose={() => useRunStore.setState({ lastCombat: null })}
        />
      )}
    </div>
  );
}
