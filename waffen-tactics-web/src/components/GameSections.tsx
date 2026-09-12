import type { CombatUnitRoundStats } from '../hooks/combat/types'
import type { PlayerState } from '../store/gameStore'
import type { Item } from '../data/items'
import { Panel } from '../ui/primitives'
import Bench from './Bench'
import GameBoard from './GameBoard'
import ItemsPanel from './ItemsPanel'
import Shop from './Shop'

interface GameSectionsProps {
  playerState: PlayerState
  itemCatalog: Item[]
  isGameOver: boolean
  lastRoundStatsByUnit: Record<string, CombatUnitRoundStats>
  draggedItemId: string | null
  onUpdate: (state: PlayerState) => void
  onNotification: (message: string, type?: 'error' | 'success' | 'info') => void
  onEquipItem: (instanceId: string, itemId: string) => Promise<void>
  onItemDragStart: (itemId: string) => void
  onItemDragEnd: () => void
}

export default function GameSections({
  playerState,
  itemCatalog,
  isGameOver,
  lastRoundStatsByUnit,
  draggedItemId,
  onUpdate,
  onNotification,
  onEquipItem,
  onItemDragStart,
  onItemDragEnd,
}: GameSectionsProps) {
  return (
    <>
      {!isGameOver && (
        <ItemsPanel
          playerState={playerState}
          onUpdate={onUpdate}
          onNotification={onNotification}
          itemCatalog={itemCatalog}
          onItemDragStart={onItemDragStart}
          onItemDragEnd={onItemDragEnd}
        />
      )}

      <Panel variant="raised" className="game-section p-4">
        <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
          <span>🎯</span> Plansza bojowa
          <span className={`text-sm font-mono ${
            playerState.board.length >= playerState.max_board_size
              ? 'text-yellow-500'
              : 'text-text/60'
          }`}>
            [{playerState.board.length}/{playerState.max_board_size}]
          </span>
          {isGameOver && <span className="text-sm text-red-500 font-normal ml-2">(Gra zakończona - tylko podgląd)</span>}
        </h2>
        <GameBoard
          playerState={playerState}
          onUpdate={onUpdate}
          onNotification={onNotification}
          onEquipItem={onEquipItem}
          roundStatsByUnit={lastRoundStatsByUnit}
          itemCatalog={itemCatalog}
          draggedItemId={draggedItemId}
        />
      </Panel>

      <Panel variant="raised" className="game-section p-4">
        <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
          <span>📦</span> Ławka
          <span className={`text-sm font-mono ${
            playerState.bench.length >= playerState.max_bench_size
              ? 'text-red-500'
              : 'text-text/60'
          }`}>
            [{playerState.bench.length}/{playerState.max_bench_size}]
          </span>
        </h2>
        <Bench
          playerState={playerState}
          onUpdate={onUpdate}
          onNotification={onNotification}
          onEquipItem={onEquipItem}
          itemCatalog={itemCatalog}
          draggedItemId={draggedItemId}
        />
      </Panel>

      {!isGameOver && (
        <Panel variant="raised" className="game-section p-4">
          <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
            <span>🛍️</span> Sklep
          </h2>
          <Shop playerState={playerState} onUpdate={onUpdate} onNotification={onNotification} />
        </Panel>
      )}
    </>
  )
}

