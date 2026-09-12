import { Button } from '../ui/primitives'
import TopDetailedToggle from './TopDetailedToggle'

type HeaderUser = {
  username?: string | null
} | null

interface GameHeaderProps {
  user: HeaderUser
  playerState: {
    hp: number
    level: number
    gold: number
    wins: number
    streak: number
    round_number: number
    board: unknown[]
  }
  playerAvatarUrl: string | null
  isGameOver: boolean
  onStartCombat: () => void
  onSurrender: () => void
  onShowTraits: () => void
  onShowLeaderboard: () => void
  onLogout: () => void
}

export default function GameHeader({
  user,
  playerState,
  playerAvatarUrl,
  isGameOver,
  onStartCombat,
  onSurrender,
  onShowTraits,
  onShowLeaderboard,
  onLogout,
}: GameHeaderProps) {
  return (
    <header className="game-topbar bg-surface/80 backdrop-blur-md border-b border-primary/20 sticky top-0 z-50">
      <div className="game-topbar-inner container mx-auto px-4 py-3">
        <div className="game-topbar-row flex items-center justify-between">
          <div className="game-topbar-player flex items-center gap-4">
            {playerAvatarUrl ? (
              <img
                src={playerAvatarUrl}
                alt="Avatar"
                className="w-12 h-12 rounded-full ring-2 ring-primary/30"
              />
            ) : (
              <div
                role="img"
                aria-label="Brak avatara"
                className="w-12 h-12 rounded-full ring-2 ring-primary/30 bg-slate-700 flex items-center justify-center font-bold text-primary"
              >
                {user?.username?.charAt(0).toUpperCase() || '?'}
              </div>
            )}
            <div className="flex items-center gap-4">
              <div>
                <div className="text-sm font-bold">{user?.username}</div>
                <div className="text-xs text-text/60">Runda {playerState.round_number}</div>
              </div>
              <div className="game-topbar-stats flex items-center gap-3 text-sm">
                <div className={`flex items-center gap-1 px-2 py-1 rounded ${playerState.hp <= 0 ? 'bg-red-500/40 animate-pulse' : 'bg-red-500/20'}`}>
                  <span>❤️</span>
                  <span className="font-bold">{playerState.hp}</span>
                </div>
                <div className="flex items-center gap-1 bg-blue-500/20 px-2 py-1 rounded">
                  <span>⭐</span>
                  <span className="font-bold">Lvl {playerState.level}</span>
                </div>
                <div className="flex items-center gap-1 bg-yellow-500/20 px-2 py-1 rounded">
                  <span>💰</span>
                  <span className="font-bold">{playerState.gold}</span>
                </div>
                <div className="flex items-center gap-1 bg-green-500/20 px-2 py-1 rounded">
                  <span>🏆</span>
                  <span className="font-bold">{playerState.wins}W</span>
                </div>
                <div className="flex items-center gap-1 bg-green-500/20 px-2 py-1 rounded">
                  <span>🔥</span>
                  <span className="font-bold">{playerState.streak}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="game-topbar-actions flex items-center gap-3">
            {!isGameOver && (
              <>
                <Button
                  variant="danger"
                  onClick={onStartCombat}
                  disabled={playerState.board.length === 0}
                  className="px-6 py-2 font-bold"
                >
                  ⚔️ WALCZ!
                </Button>
                <Button variant="secondary" onClick={onSurrender} className="px-4 py-2 text-sm" title="Poddaj się">
                  🏳️ Poddaj się
                </Button>
              </>
            )}
            <Button variant="secondary" onClick={onShowTraits} className="px-4 py-2 text-sm" title="Informacje o traitach">
              📚 Info
            </Button>
            <Button variant="secondary" onClick={onShowLeaderboard} className="px-4 py-2 text-sm" title="Tablica wyników">
              🏆 Ranking
            </Button>
            <Button variant="danger" onClick={onLogout}>
              🚪 Wyloguj
            </Button>
            <TopDetailedToggle />
          </div>
        </div>
      </div>
    </header>
  )
}

