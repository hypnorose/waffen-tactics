interface GameStatsProps {
  playerState: any
}

export default function GameStats({ playerState }: GameStatsProps) {
  // Use XP data from backend
  const xpForNext = playerState.xp_to_next_level || 0
  const xpProgress = xpForNext > 0 ? Math.min((playerState.xp / xpForNext) * 100, 100) : 100

  return (
    <div className="card">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {/* HP */}
        <div className="text-center">
          <div className="text-2xl font-bold text-red-500">{playerState.hp} ❤️</div>
          <div className="text-sm text-text/60">Życie</div>
        </div>

        {/* Level */}
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-500">Lvl {playerState.level}</div>
          <div className="text-sm text-text/60">Poziom</div>
        </div>

        {/* XP */}
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-500">
            {playerState.xp}/{xpForNext} XP
          </div>
          <div className="w-full bg-surface/50 rounded-full h-2 mt-1">
            <div
              className="bg-purple-500 h-2 rounded-full transition-all"
              style={{ width: `${xpProgress}%` }}
            />
          </div>
        </div>

        {/* Gold */}
        <div className="text-center">
          <div className="text-2xl font-bold text-yellow-500">{playerState.gold} 🪙</div>
          <div className="text-sm text-text/60">Złoto</div>
        </div>

        {/* Wins */}
        <div className="text-center">
          <div className="text-2xl font-bold text-green-500">{playerState.wins} 🏆</div>
          <div className="text-sm text-text/60">Wygrane</div>
        </div>
      </div>

      {/* Round */}
      <div className="mt-4 text-center text-sm text-text/60">
        Runda {playerState.round_number}
      </div>
    </div>
  )
}
