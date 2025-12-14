import { useEffect, useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { useGameStore } from '../store/gameStore'
import { gameAPI } from '../services/api'
import GameBoard from '../components/GameBoard'
import Shop from '../components/Shop'
import Bench from '../components/Bench'
import TopDetailedToggle from '../components/TopDetailedToggle'
import CombatOverlay from '../components/CombatOverlay'
import { loadUnits } from '../data/units'

export default function Game() {
  const { user, logout } = useAuthStore()
  const { playerState, setPlayerState, setLoading, setError } = useGameStore()
  const [showCombat, setShowCombat] = useState(false)
  const [isGameOver, setIsGameOver] = useState(false)
  const [showLeaderboard, setShowLeaderboard] = useState(false)
  const [leaderboard, setLeaderboard] = useState<any[]>([])

  useEffect(() => {
    initGame()
  }, [])
  
  useEffect(() => {
    // Check if game is over
    if (playerState && playerState.hp <= 0) {
      setIsGameOver(true)
    }
  }, [playerState])
  
  const initGame = async () => {
    // Load units first
    await loadUnits()
    // Then load game state
    await loadGameState()
  }

  const loadGameState = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Try to get existing game state
      const response = await gameAPI.getPlayerState()
      setPlayerState(response.data)
      setLoading(false)
    } catch (err: any) {
      // If no game found, start new game
      if (err.response?.data?.needs_start) {
        try {
          const startResponse = await gameAPI.startGame()
          setPlayerState(startResponse.data)
          setLoading(false)
        } catch (startErr) {
          console.error('Failed to start game:', startErr)
          setError('Nie można rozpocząć gry')
          setLoading(false)
        }
      } else {
        console.error('Failed to load game:', err)
        setError('Nie można załadować gry')
        setLoading(false)
      }
    }
  }

  const handleStartCombat = () => {
    if (!playerState || playerState.board.length === 0) {
      alert('Dodaj jednostki na planszę!')
      return
    }
    setShowCombat(true)
  }

  const handleCombatEnd = (newState?: any) => {
    setShowCombat(false)
    if (newState) {
      setPlayerState(newState)
    }
  }

  const handleReset = async () => {
    if (!confirm('Czy na pewno chcesz zresetować grę? Twoje wyniki zostaną zapisane do tablicy wyników.')) {
      return
    }
    
    setLoading(true)
    try {
      const response = await gameAPI.resetGame()
      // resetGame saves to leaderboard and creates a fresh player, but to ensure the
      // shop is generated (same behavior as surrender), call startGame() afterwards.
      try {
        const startResp = await gameAPI.startGame()
        setPlayerState(startResp.data)
        setIsGameOver(false)
        alert((response.data && response.data.message) ? `${response.data.message} Nowa gra rozpoczęta.` : 'Gra zresetowana. Nowa gra rozpoczęta.')
      } catch (startErr) {
        // If starting a new game fails, fall back to the state returned by resetGame
        setPlayerState(response.data.state)
        setIsGameOver(false)
        console.error('Failed to call startGame after reset:', startErr)
        alert((response.data && response.data.message) ? `${response.data.message} Nie udało się automatycznie rozpocząć nowej gry.` : 'Gra zresetowana. Nie udało się rozpocząć nowej gry.')
      }
    } catch (err: any) {
      alert(err.response?.data?.error || 'Nie można zresetować gry')
    } finally {
      setLoading(false)
    }
  }

  const handleSurrender = async () => {
    if (!confirm('Czy na pewno chcesz się poddać? Gra zostanie zakończona i wyniki zapisane.')) {
      return
    }
    
    setLoading(true)
    try {
      const response = await gameAPI.surrender()
      // Save final state (surrender saved to leaderboard). Then immediately start a new game.
      try {
        const startResp = await gameAPI.startGame()
        setPlayerState(startResp.data)
        setIsGameOver(false)
        alert((response.data && response.data.message) ? `${response.data.message} Nowa gra rozpoczęta.` : 'Poddano się. Nowa gra rozpoczęta.')
      } catch (startErr) {
        // If starting new game fails, keep surrendered state but notify user
        setPlayerState(response.data.state)
        setIsGameOver(true)
        console.error('Failed to start new game after surrender:', startErr)
        alert((response.data && response.data.message) ? `${response.data.message} Nie udało się automatycznie rozpocząć nowej gry.` : 'Poddano się. Nie udało się rozpocząć nowej gry.')
      }
    } catch (err: any) {
      alert(err.response?.data?.error || 'Nie można się poddać')
    } finally {
      setLoading(false)
    }
  }

  const handleShowLeaderboard = async () => {
    setShowLeaderboard(true)
    try {
      const response = await gameAPI.getLeaderboard()
      setLeaderboard(response.data)
    } catch (err) {
      console.error('Failed to load leaderboard:', err)
      setLeaderboard([])
    }
  }

  if (!playerState) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-2xl animate-pulse">Ładowanie gry...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-surface/30">
      {/* Game Over Overlay */}
      {isGameOver && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-surface border-2 border-red-500 rounded-lg p-8 max-w-md w-full mx-4 text-center space-y-4">
            <div className="text-6xl mb-4">💀</div>
            <h1 className="text-3xl font-bold text-red-500">KONIEC GRY!</h1>
            <div className="space-y-2 text-text/80">
              <p className="text-xl">Twoje statystyki:</p>
              <div className="flex justify-around text-sm">
                <div>
                  <div className="text-2xl font-bold text-green-500">{playerState.wins}</div>
                  <div className="text-xs">Zwycięstwa</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-red-500">{playerState.losses}</div>
                  <div className="text-xs">Porażki</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-blue-500">{playerState.level}</div>
                  <div className="text-xs">Poziom</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-yellow-500">{playerState.round_number}</div>
                  <div className="text-xs">Runda</div>
                </div>
              </div>
            </div>
            <p className="text-sm text-text/60">Twoje wyniki zostały zapisane do tablicy wyników!</p>
            <button
              onClick={handleReset}
              className="w-full btn bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 py-3 font-bold"
            >
              🔄 Nowa Gra
            </button>
          </div>
        </div>
      )}

      {/* Top Bar - Avatar, HP, Level, Username, Wyloguj */}
      <div className="bg-surface/80 backdrop-blur-md border-b border-primary/20 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            {/* Left: Avatar + User Info + Stats */}
            <div className="flex items-center gap-4">
              <img
                src={`https://cdn.discordapp.com/avatars/${user?.id}/${user?.avatar}.png`}
                alt="Avatar"
                className="w-12 h-12 rounded-full ring-2 ring-primary/30"
              />
              <div className="flex items-center gap-4">
                <div>
                  <div className="text-sm font-bold">{user?.username}</div>
                  <div className="text-xs text-text/60">Runda {playerState.round_number}</div>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  {/* HP */}
                  <div className={`flex items-center gap-1 px-2 py-1 rounded ${playerState.hp <= 0 ? 'bg-red-500/40 animate-pulse' : 'bg-red-500/20'}`}>
                    <span>❤️</span>
                    <span className="font-bold">{playerState.hp}</span>
                  </div>
                  
                  {/* Level */}
                  <div className="flex items-center gap-1 bg-blue-500/20 px-2 py-1 rounded">
                    <span>⭐</span>
                    <span className="font-bold">Lvl {playerState.level}</span>
                  </div>
                  
                  {/* Gold */}
                  <div className="flex items-center gap-1 bg-yellow-500/20 px-2 py-1 rounded">
                    <span>🪙</span>
                    <span className="font-bold">{playerState.gold}</span>
                  </div>
                  
                  {/* Wins */}
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
            
            {/* Right: Combat/Surrender Buttons + Leaderboard + Logout + Global Toggle */}
            <div className="flex items-center gap-3">
              {!isGameOver && (
                <>
                  <button
                    onClick={handleStartCombat}
                    disabled={playerState.board.length === 0}
                    className="btn bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-700 hover:to-orange-700 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-2 font-bold"
                  >
                    ⚔️ WALCZ!
                  </button>
                  <button
                    onClick={handleSurrender}
                    className="btn bg-gray-600 hover:bg-gray-700 px-4 py-2 text-sm"
                    title="Poddaj się"
                  >
                    🏳️ Poddaj się
                  </button>
                </>
              )}
              <button
                onClick={handleShowLeaderboard}
                className="btn bg-yellow-600 hover:bg-yellow-700 px-4 py-2 text-sm"
                title="Tablica wyników"
              >
                🏆 Ranking
              </button>
              <button onClick={logout} className="btn btn-danger">
                🚪 Wyloguj
              </button>
              {/* Detailed view toggle (global) */}
              <TopDetailedToggle />
            </div>
          </div>
        </div>
      </div>

      <div className={`container mx-auto px-4 py-6 max-w-7xl space-y-4 ${isGameOver ? 'pointer-events-none opacity-50' : ''}`}>
        {/* Board Section */}
        <div className="card">
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
          <GameBoard playerState={playerState} onUpdate={setPlayerState} />
        </div>

        {/* Bench Section */}
        <div className="card">
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
          <Bench playerState={playerState} onUpdate={setPlayerState} />
        </div>

        {/* Shop Section */}
        {!isGameOver && (
          <div className="card">
            <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
              <span>🛍️</span> Sklep
            </h2>
            <Shop playerState={playerState} onUpdate={setPlayerState} />
          </div>
        )}
      </div>

      {/* Combat Overlay */}
      {showCombat && <CombatOverlay onClose={handleCombatEnd} />}

      {/* Leaderboard Modal */}
      {showLeaderboard && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface border-2 border-yellow-500 rounded-lg max-w-3xl w-full max-h-[80vh] overflow-auto">
            <div className="sticky top-0 bg-surface border-b border-yellow-500/20 p-6 flex items-center justify-between">
              <h2 className="text-2xl font-bold flex items-center gap-2">
                <span>🏆</span> Tablica Wyników
              </h2>
              <button
                onClick={() => setShowLeaderboard(false)}
                className="btn bg-red-600 hover:bg-red-700 px-4 py-2"
              >
                ✕ Zamknij
              </button>
            </div>
            
            <div className="p-6">
              {leaderboard.length === 0 ? (
                <p className="text-center text-text/60 py-8">Brak wyników w tabeli.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-primary/20">
                        <th className="text-left py-3 px-2">#</th>
                        <th className="text-left py-3 px-2">Gracz</th>
                        <th className="text-center py-3 px-2">Zwycięstwa</th>
                        <th className="text-center py-3 px-2">Porażki</th>
                        <th className="text-center py-3 px-2">Poziom</th>
                        <th className="text-center py-3 px-2">Runda</th>
                        <th className="text-left py-3 px-2">Data</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leaderboard.map((entry, index) => (
                        <tr 
                          key={index} 
                          className={`border-b border-primary/10 hover:bg-primary/5 ${
                            index === 0 ? 'bg-yellow-500/10' : 
                            index === 1 ? 'bg-gray-400/10' : 
                            index === 2 ? 'bg-orange-600/10' : ''
                          }`}
                        >
                          <td className="py-3 px-2 font-bold">
                            {index === 0 && '🥇'}
                            {index === 1 && '🥈'}
                            {index === 2 && '🥉'}
                            {index > 2 && `${index + 1}.`}
                          </td>
                          <td className="py-3 px-2 font-medium">{entry[0]}</td>
                          <td className="py-3 px-2 text-center text-green-500 font-bold">{entry[1]}</td>
                          <td className="py-3 px-2 text-center text-red-500">{entry[2]}</td>
                          <td className="py-3 px-2 text-center text-blue-500">{entry[3]}</td>
                          <td className="py-3 px-2 text-center text-yellow-500">{entry[4]}</td>
                          <td className="py-3 px-2 text-text/60 text-xs">{new Date(entry[5]).toLocaleString('pl-PL')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
